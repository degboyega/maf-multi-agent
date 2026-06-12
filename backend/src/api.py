"""FastAPI server with SSE endpoint for real-time multi-agent orchestration."""

import asyncio
import json
import logging
import os
import re
import uuid
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path
from typing import AsyncGenerator

import yaml

from dotenv import load_dotenv

# Load env vars from .env before any config reads. Search common locations:
# backend/.env, then repo-root .env (one level up from backend/).
for _env_candidate in (
    Path(__file__).resolve().parent.parent / ".env",
    Path(__file__).resolve().parent.parent.parent / ".env",
):
    if _env_candidate.exists():
        load_dotenv(_env_candidate, override=False)

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response, StreamingResponse
from pydantic import BaseModel

from src.config import get_config
from src.events import AgentEvent, EventType
from src.agent_loader import list_agent_definitions
from src.graph_mail_client import send_mail
from src.scratchpad.mail_tools import PENDING_MAIL_STORE
from src.scratchpad.schedule_tools import PENDING_SCHEDULE_STORE
from src.fabric_capacity import get_fabric_capacity_status, resume_fabric_capacity
from src.file_store import (
    copy_run_files,
    get_all_files,
    get_file,
    rewrite_sandbox_urls,
    rewrite_sandbox_urls_for_disk,
)
from src.history_store import get_history_store
from src.run_store import RunStore

logger = logging.getLogger(__name__)


def _extract_email_from_token(token: str | None) -> str | None:
    """Best-effort email extraction from a JWT access token.

    WARNING: This does NOT verify the token signature. It is safe to use ONLY
    when the token has already been validated by an upstream gateway (e.g., Azure
    Container Apps Easy Auth). Never use this as the sole identity check.

    The primary identity source is _resolve_user_email() which reads the
    pre-validated X-MS-CLIENT-PRINCIPAL-NAME header from Easy Auth.
    """
    if not token:
        return None
    try:
        import base64
        parts = token.split(".")
        if len(parts) < 2:
            return None
        payload = parts[1] + "=" * (-len(parts[1]) % 4)
        claims = json.loads(base64.urlsafe_b64decode(payload))
        return claims.get("preferred_username") or claims.get("upn") or None
    except Exception:
        return None


# Regex: strip chars unsafe for directory names (keep alphanumeric, @, ., -, _)
_SAFE_EMAIL_RE = re.compile(r"[^a-zA-Z0-9@.\-_]")


def _safe_user_dir(email: str) -> str:
    """Sanitize an email address into a safe directory name."""
    return _SAFE_EMAIL_RE.sub("_", email.lower().strip())


def _allow_anonymous_local_dev() -> bool:
    """Return whether unauthenticated local-dev fallbacks are explicitly enabled."""
    return get_config().allow_anonymous_local_dev


def _resolve_user_email(request: Request) -> str | None:
    """Extract user email from trusted Easy Auth headers.

    Query-string identity is accepted only in explicit local development mode.
    """
    principal = request.headers.get("X-MS-CLIENT-PRINCIPAL-NAME")
    if principal:
        return principal
    if _allow_anonymous_local_dev():
        return request.query_params.get("user_email") or None
    return None


def _require_history_user_email(request: Request) -> str | None:
    """Require authenticated identity for persisted history/result access."""
    user_email = _resolve_user_email(request)
    if user_email or _allow_anonymous_local_dev():
        return user_email
    raise HTTPException(status_code=401, detail="Authenticated user identity is required")


def _is_super_user(user_email: str | None) -> bool:
    """Check if the authenticated user is the configured super-user."""
    if not user_email:
        return False
    su = get_config().super_user_email
    return bool(su and user_email.lower().strip() == su.lower().strip())


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize logging and observability on startup."""
    setup_logging()
    from src.observability import setup_observability
    await setup_observability()
    app.state.run_store = RunStore()
    yield


app = FastAPI(title="MAF & Foundry Agent Orchestration", lifespan=lifespan)

_config = get_config()
_origins = [o.strip() for o in _config.allowed_origins.split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _store(request_or_app=None) -> RunStore:
    """Return the RunStore instance from app state."""
    return app.state.run_store


class RunRequest(BaseModel):
    query: str
    selected_agents: list[str] | None = None
    reasoning_effort: str | None = "low"  # "high", "medium", "low", or "none"
    user_token: str | None = None  # Fabric user token (Easy Auth header or body)
    user_email: str | None = None  # Local-dev identity fallback only; gated by config
    conversation_run_id: str | None = None  # Previous run_id to continue a conversation


class RunResponse(BaseModel):
    run_id: str


def _serialize_event(event: AgentEvent) -> dict:
    """Convert an AgentEvent into the persisted snapshot format."""
    return {
        "event_type": event.event_type.value,
        "source": event.source,
        "data": event.data,
        "timestamp": event.timestamp,
        "event_summary": event.event_summary,
    }


class _RunSnapshotWriter:
    """Persist the latest run snapshot while the workflow is still active."""

    def __init__(
        self,
        run_id: str,
        user_dir: str,
        query: str,
        created_at: str,
        user_email: str | None = None,
    ):
        self.run_id = run_id
        self.user_dir = user_dir
        self.query = query
        self.created_at = created_at
        self.user_email = user_email
        self.events: list[dict] = []
        self.result_text = ""
        self.document_md = ""
        self.status = "running"
        self._dirty = False
        self._flush_task: asyncio.Task | None = None
        self._flush_lock = asyncio.Lock()

    def record_event(self, serialized_event: dict) -> None:
        """Add an event to the snapshot state and queue a checkpoint save."""
        self.events.append(serialized_event)

        event_type = serialized_event.get("event_type")
        data = serialized_event.get("data", {})
        source = serialized_event.get("source")

        if event_type == EventType.OUTPUT.value:
            if isinstance(data.get("text"), str):
                self.result_text = data["text"]
            if isinstance(data.get("document"), str):
                self.document_md = data["document"]
        elif event_type == EventType.AGENT_ERROR.value and source == "orchestrator":
            self.status = "error"

        self._dirty = True
        if self._flush_task is None or self._flush_task.done():
            self._flush_task = asyncio.create_task(self._flush_loop())

    def set_terminal_state(
        self,
        status: str,
        result_text: str = "",
        document_md: str = "",
    ) -> None:
        """Capture the final run state before the terminal checkpoint is written."""
        self.status = status
        if result_text:
            self.result_text = result_text
        if document_md:
            self.document_md = document_md

    async def flush_now(self, include_files: bool = False) -> None:
        """Write the latest run snapshot to the configured history store."""
        async with self._flush_lock:
            snapshot = _build_session_snapshot(
                run_id=self.run_id,
                query=self.query,
                events=self.events,
                result_text=self.result_text,
                document_md=self.document_md,
                status=self.status,
                created_at=self.created_at,
                user_email=self.user_email,
            )
            await _persist_session_snapshot(
                user_dir=self.user_dir,
                run_id=self.run_id,
                snapshot=snapshot,
                include_files=include_files,
            )

    async def _flush_loop(self) -> None:
        while self._dirty:
            self._dirty = False
            try:
                await self.flush_now()
            except Exception as e:
                logger.warning("⚠️  Failed to checkpoint run %s: %s", self.run_id, e)


@app.get("/api/agents")
async def get_agents():
    """Return available agent definitions with avatar and role metadata."""
    # Always include the orchestrator as a built-in agent
    agents = [
        {
            "name": "orchestrator",
            "display_name": "Orchestrator",
            "avatar": "🤖",
            "role": "Facilitator & Coordinator",
            "model": "gpt-5.1",
            "description": "Coordinates all specialist agents, plans tasks, and synthesizes results.",
        }
    ]
    for ad in list_agent_definitions():
        agents.append({
            "name": ad.name,
            "display_name": ad.display_name,
            "avatar": ad.avatar,
            "role": ad.role,
            "model": ad.model,
            "description": ad.description,
        })
    return agents


@app.get("/api/version")
async def get_version():
    """Return build version info injected at Docker build time."""
    return {
        "version": os.getenv("APP_VERSION", "dev"),
        "git_sha": os.getenv("GIT_SHA", "unknown"),
        "build_date": os.getenv("BUILD_DATE", "unknown"),
    }


def _event_to_sse(event: AgentEvent) -> str:
    """Serialize an AgentEvent to an SSE data line.

    Rewrites ``sandbox:`` URLs in text fields so the frontend can
    render images via the ``/api/files/`` endpoint.
    """
    data = event.data

    # Rewrite sandbox: URLs in text fields destined for the frontend
    _TEXT_KEYS = ("text", "result", "content")
    rewritten = False
    for key in _TEXT_KEYS:
        val = data.get(key)
        if isinstance(val, str) and "sandbox:" in val:
            if not rewritten:
                data = dict(data)  # shallow copy once
                rewritten = True
            data[key] = rewrite_sandbox_urls(val)

    payload = {
        "event_type": event.event_type.value,
        "source": event.source,
        "data": data,
        "timestamp": event.timestamp,
        "event_summary": event.event_summary,
    }
    return f"data: {json.dumps(payload)}\n\n"


_SCHEDULE_QUERY = (
    "Run the weekly health analysis for COMP-001 (Houston, TX) and COMP-002 (Midland, TX). "
    "Retrieve the last 7 days of sensor data, check all readings against the Emerson CSER2000 "
    "advisory and alarm thresholds and Iqbal maintenance guidelines, cross-reference the "
    "maintenance history for recurring fault patterns, and assess overall risk for each asset. "
    "Produce a structured weekly health report with: status per asset (Normal / Advisory / Critical), "
    "specific threshold breaches with measured values, root cause hypothesis, and recommended actions "
    "with urgency rating. When the report is complete, send it to the engineering team for review."
)


@app.post("/api/schedule/trigger")
async def schedule_trigger(request: Request):
    """Logic App webhook — starts a scheduled health analysis run. Authenticated via X-Schedule-Api-Key header."""
    cfg = get_config()
    if not cfg.schedule_api_key:
        raise HTTPException(status_code=503, detail="Scheduled triggers are not configured")
    provided_key = request.headers.get("X-Schedule-Api-Key", "")
    if provided_key != cfg.schedule_api_key:
        raise HTTPException(status_code=401, detail="Invalid schedule API key")

    created_at = datetime.now().isoformat()
    run_id = datetime.now().strftime("%Y%m%d-%H%M%S") + "-" + uuid.uuid4().hex[:6]
    user_email = cfg.schedule_recipient_email or None
    user_dir = _safe_user_dir(user_email) if user_email else ""

    store = _store()
    run_state = store.create(run_id, user_dir=user_dir)
    queue = run_state.queue
    snapshot_writer = _RunSnapshotWriter(
        run_id=run_id,
        user_dir=user_dir,
        query=_SCHEDULE_QUERY,
        created_at=created_at,
        user_email=user_email,
    )
    await snapshot_writer.flush_now()

    loop = asyncio.get_running_loop()

    def _handle_event(event: AgentEvent):
        if event.event_type != EventType.AGENT_STREAMING:
            serialized = _serialize_event(event)
            snapshot_writer.record_event(serialized)
        queue.put_nowait(event)

    def event_callback(event: AgentEvent):
        loop.call_soon_threadsafe(_handle_event, event)

    asyncio.create_task(
        _run_scheduled_analysis(run_id, event_callback, snapshot_writer, user_email)
    )

    logger.info("⏰ SCHEDULED RUN %s triggered by Logic App", run_id)
    return {"run_id": run_id, "status": "triggered"}


async def _run_scheduled_analysis(run_id, event_callback, snapshot_writer, user_email):
    """Run the weekly health analysis and auto-send the report — no confirmation gate."""
    from src.scratchpad.workflow import run_scratchpad_workflow
    from src.scratchpad.pptx_builder import build_health_report_pptx

    cfg = get_config()
    try:
        result_text, document_md = await run_scratchpad_workflow(
            query=_SCHEDULE_QUERY,
            event_callback=event_callback,
            user_email=user_email,
        )
        snapshot_writer.set_terminal_state(status="done", result_text=result_text, document_md=document_md)
        await snapshot_writer.flush_now()
    except Exception as exc:
        logger.error("❌ Scheduled workflow failed: %s", exc)
        return

    if not (cfg.mail_enabled and user_email and result_text):
        logger.info("⏰ Scheduled run %s complete — mail disabled or no result", run_id)
        return

    # Convert result markdown to HTML
    lines = result_text.strip().split("\n")
    html_lines = []
    for line in lines:
        if line.startswith("## "):
            html_lines.append(f"<h2>{line[3:]}</h2>")
        elif line.startswith("### "):
            html_lines.append(f"<h3>{line[4:]}</h3>")
        elif line.startswith("**") and line.endswith("**"):
            html_lines.append(f"<p><strong>{line[2:-2]}</strong></p>")
        elif line.startswith("- ") or line.startswith("* "):
            html_lines.append(f"<li>{line[2:]}</li>")
        elif line.strip():
            html_lines.append(f"<p>{line}</p>")
    body_html = "<html><body style='font-family:Calibri,sans-serif'>" + "".join(html_lines) + "</body></html>"

    # Generate PPTX
    pptx_bytes = build_health_report_pptx(body_html, "Weekly MAF Health Report")

    attachments = None
    if pptx_bytes:
        filename = f"MAF_Health_Report_{datetime.now().strftime('%Y-%m-%d')}.pptx"
        attachments = [{
            "name": filename,
            "content_type": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
            "data": pptx_bytes,
        }]

    cc_addresses = [a.strip() for a in cfg.mail_team_addresses.split(",") if a.strip()] or None
    subject = f"MAF Weekly Compressor Health Report — {datetime.now().strftime('%d %b %Y')}"

    result = await send_mail(
        sender=cfg.mail_sender_address,
        to=user_email,
        subject=subject,
        body_html=body_html,
        cc=cc_addresses,
        attachments=attachments,
    )
    logger.info("📧 Scheduled report emailed: %s", result)


@app.post("/api/run", response_model=RunResponse)
async def start_run(req: RunRequest, request: Request):
    """Start a new scratchpad workflow run. Returns a run_id for SSE streaming."""
    created_at = datetime.now().isoformat()
    run_id = datetime.now().strftime("%Y%m%d-%H%M%S") + "-" + uuid.uuid4().hex[:6]

    # Resolve Fabric user token: Easy Auth header (ACA) > body field (local dev) > None
    user_token = (
        request.headers.get("X-MS-TOKEN-AAD-ACCESS-TOKEN")
        or req.user_token
        or None
    )
    token_source = (
        "easyauth-header" if request.headers.get("X-MS-TOKEN-AAD-ACCESS-TOKEN")
        else "body" if req.user_token
        else "absent"
    )

    # Resolve user email only from trusted server-side identity sources.
    # Body/query fallbacks are allowed only in explicit local development mode.
    principal_email = request.headers.get("X-MS-CLIENT-PRINCIPAL-NAME")
    if principal_email:
        user_email = principal_email
    elif request.headers.get("X-MS-TOKEN-AAD-ACCESS-TOKEN"):
        user_email = _extract_email_from_token(request.headers.get("X-MS-TOKEN-AAD-ACCESS-TOKEN"))
    elif _allow_anonymous_local_dev():
        user_email = req.user_email or _extract_email_from_token(req.user_token)
    else:
        user_email = None

    logger.info("🚀 RUN %s | user_token=%s | user_email=%s", run_id, token_source, user_email or "absent")

    # Build conversation history from previous run if continuing a session
    conversation_history: str | None = None
    if req.conversation_run_id:
        history = get_history_store()
        user_dir_for_lookup = _safe_user_dir(user_email) if user_email else ""
        prev_session = await history.get_session(user_dir_for_lookup, req.conversation_run_id)
        if not prev_session and user_email:
            result_tuple = await history.find_session_any_user(req.conversation_run_id)
            prev_session = result_tuple[1] if result_tuple else None
        if prev_session:
            prev_query = prev_session.get("query", "")
            prev_result = prev_session.get("result", "")
            if prev_query and prev_result:
                conversation_history = (
                    f"Previous conversation turn:\n"
                    f"User asked: {prev_query}\n"
                    f"Result was: {prev_result}\n"
                )
                logger.info("💬 Conversation continued from run %s", req.conversation_run_id)
        else:
            logger.warning("💬 conversation_run_id %s not found — starting fresh", req.conversation_run_id)

    store = _store()
    user_dir = _safe_user_dir(user_email) if user_email else ""
    run_state = store.create(run_id, user_dir=user_dir)
    queue = run_state.queue
    snapshot_writer = _RunSnapshotWriter(
        run_id=run_id,
        user_dir=user_dir,
        query=req.query,
        created_at=created_at,
        user_email=user_email,
    )
    await snapshot_writer.flush_now()

    # Event callback bridges sync calls into the async queue
    loop = asyncio.get_running_loop()

    def _handle_event(event: AgentEvent):
        if event.event_type != EventType.AGENT_STREAMING:
            serialized = _serialize_event(event)
            snapshot_writer.record_event(serialized)
            logger.info(
                "EVENT [%s] source=%s | %s",
                event.event_type.value,
                event.source,
                json.dumps(event.data, default=str)[:200],
            )
        queue.put_nowait(event)

    def event_callback(event: AgentEvent):
        loop.call_soon_threadsafe(_handle_event, event)

    # Run workflow in background task
    asyncio.create_task(
        _run_workflow(
            run_id,
            req.query,
            event_callback,
            snapshot_writer=snapshot_writer,
            selected_agents=req.selected_agents,
            reasoning_effort=req.reasoning_effort,
            user_token=user_token,
            user_email=user_email,
            conversation_history=conversation_history,
        )
    )

    return RunResponse(run_id=run_id)


async def _run_workflow(
    run_id: str,
    query: str,
    event_callback,
    snapshot_writer: _RunSnapshotWriter,
    selected_agents: list[str] | None = None,
    reasoning_effort: str | None = "low",
    user_token: str | None = None,
    user_email: str | None = None,
    conversation_history: str | None = None,
):
    """Execute the scratchpad workflow and push events to the queue."""
    store = _store()
    run_state = store.get(run_id)
    if not run_state:
        logger.error("Run %s not found in store", run_id)
        return
    queue = run_state.queue
    workflow_status = "done"
    user_dir = _safe_user_dir(user_email) if user_email else ""

    # Ensure local output dir exists for markdown artifacts + sandbox files
    output_dir = _get_output_dir()
    local_run_dir = os.path.join(output_dir, user_dir, run_id) if user_dir else os.path.join(output_dir, run_id)
    os.makedirs(local_run_dir, exist_ok=True)

    try:
        from src.scratchpad.workflow import run_scratchpad_workflow

        result_text, document_md = await run_scratchpad_workflow(
            query, event_callback=event_callback,
            selected_agents=selected_agents,
            reasoning_effort=reasoning_effort,
            user_token=user_token,
            user_email=user_email,
            conversation_history=conversation_history,
        )

        # Copy sandbox files into local run folder (for disk-based markdown)
        copy_run_files(local_run_dir)

        store.set_result(run_id, {
            "result": rewrite_sandbox_urls(result_text) if result_text else "",
            "document": rewrite_sandbox_urls(document_md) if document_md else "",
        })

        # Send final result event (URL rewriting happens in _event_to_sse)
        output_event = AgentEvent(
            event_type=EventType.OUTPUT,
            source="orchestrator",
            data={"text": result_text, "document": document_md or ""},
        )
        snapshot_writer.record_event(_serialize_event(output_event))
        snapshot_writer.set_terminal_state(
            status=workflow_status,
            result_text=result_text,
            document_md=document_md,
        )
        await queue.put(output_event)
        await snapshot_writer.flush_now(include_files=True)

    except Exception as e:
        workflow_status = "error"
        logger.exception("Workflow failed for run %s", run_id)
        error_event = AgentEvent(
            event_type=EventType.AGENT_ERROR,
            source="orchestrator",
            data={"error": str(e)},
        )
        snapshot_writer.record_event(_serialize_event(error_event))
        snapshot_writer.set_terminal_state(status="error")
        await queue.put(error_event)
        await snapshot_writer.flush_now()

    # Sentinel to signal stream end
    await queue.put(None)


_SSE_KEEPALIVE_INTERVAL = 15  # seconds between heartbeat comments


@app.get("/api/stream/{run_id}")
async def stream_events(run_id: str):
    """SSE endpoint — streams AgentEvents for a given run."""
    store = _store()
    run_state = store.get(run_id)
    if not run_state:
        raise HTTPException(status_code=404, detail="Run not found")

    # Reject duplicate connections — asyncio.Queue is single-consumer;
    # a second client would steal events from the first.
    if store.is_streaming(run_id):
        raise HTTPException(
            status_code=409,
            detail="Another client is already streaming this run",
        )
    store.set_streaming(run_id, True)

    async def event_generator() -> AsyncGenerator[str, None]:
        queue = run_state.queue
        completed_normally = False
        try:
            while True:
                try:
                    event = await asyncio.wait_for(
                        queue.get(), timeout=_SSE_KEEPALIVE_INTERVAL,
                    )
                except asyncio.TimeoutError:
                    # No event within the keepalive window — send an SSE
                    # comment to prevent proxy idle-timeout disconnects
                    # (e.g. Azure Container Apps / Envoy ingress).
                    yield ": keepalive\n\n"
                    continue

                if event is None:
                    completed_normally = True
                    # Send done sentinel
                    yield f"data: {json.dumps({'event_type': 'done'})}\n\n"
                    break
                # Skip streaming deltas — they flood the SSE connection and
                # the frontend filters them out anyway.
                if event.event_type == EventType.AGENT_STREAMING:
                    continue
                yield _event_to_sse(event)
        finally:
            store.set_streaming(run_id, False)
            if completed_normally:
                # Cleanup — remove run state to prevent memory leaks
                store.remove(run_id)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@app.get("/api/result/{run_id}")
async def get_result(run_id: str, request: Request):
    """Get the final result for a completed run."""
    _validate_run_id(run_id)
    user_email = _require_history_user_email(request)
    user_dir = _safe_user_dir(user_email) if user_email else ""
    store = _store()
    run_state = store.get(run_id)
    result = run_state.result if run_state and (_is_super_user(user_email) or run_state.user_dir == user_dir) else None
    if result is not None:
        return result

    snapshot = await _load_saved_session_for_user(run_id, user_email)
    if snapshot is None:
        raise HTTPException(status_code=404, detail="Result not found")

    result_text = snapshot.get("result", "")
    if not result_text:
        raise HTTPException(status_code=404, detail="Result not ready")

    final_document = ""
    for document in reversed(snapshot.get("documents", [])):
        if isinstance(document, dict) and isinstance(document.get("content"), str):
            final_document = document["content"]
            break

    return {"result": result_text, "document": final_document}


# ── Sandbox file serving ──────────────────────────────────────

@app.get("/api/files/{file_key:path}")
async def serve_file(file_key: str):
    """Serve a Code Interpreter sandbox file downloaded from Azure.

    The file_key is the URL-encoded sandbox path (e.g., ``%2Fmnt%2Fdata%2Fplot.png``).
    """
    import urllib.parse

    decoded_key = urllib.parse.unquote(file_key)
    entry = get_file(decoded_key)
    if entry is None:
        entry = get_file(f"sandbox:{decoded_key}")
    if entry is None and not decoded_key.startswith("/"):
        entry = get_file(f"sandbox:/{decoded_key}")
    if entry is None:
        raise HTTPException(status_code=404, detail="File not found")

    data, content_type = entry
    return Response(
        content=data,
        media_type=content_type,
        headers={
            "Cache-Control": "public, max-age=3600",
            "Content-Disposition": f"inline",
        },
    )


# ── Mail confirm / cancel ─────────────────────────────────────

@app.post("/api/mail/confirm/{token}")
async def mail_confirm(token: str):
    """Confirm and send a staged email. Called by the UI confirmation card."""
    pending = PENDING_MAIL_STORE.pop(token, None)
    if not pending:
        raise HTTPException(status_code=404, detail="Confirmation token not found or already used.")
    if pending.is_expired():
        raise HTTPException(status_code=410, detail="Confirmation token has expired. Please ask the agent to preview the email again.")

    cc = pending.team_addresses if pending.team_addresses else None
    attachments = None
    if pending.pptx_bytes:
        from datetime import datetime as _dt
        filename = f"MAF_Health_Report_{_dt.now().strftime('%Y-%m-%d')}.pptx"
        attachments = [{
            "name": filename,
            "content_type": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
            "data": pending.pptx_bytes,
        }]
    result = await send_mail(
        sender=pending.sender,
        to=pending.user_email,
        subject=pending.subject,
        body_html=pending.body,
        cc=cc,
        attachments=attachments,
    )

    if not result.startswith("Email sent"):
        logger.error("❌ Mail send failed: token=%s result=%s", token, result)
        raise HTTPException(status_code=502, detail=result)

    logger.info("✅ Mail confirmed and sent: token=%s to=%s", token, pending.user_email)
    return {"status": "sent", "result": result}


@app.post("/api/mail/cancel/{token}")
async def mail_cancel(token: str):
    """Discard a staged email without sending."""
    PENDING_MAIL_STORE.pop(token, None)
    logger.info("🚫 Mail cancelled: token=%s", token)
    return {"status": "cancelled"}


# ── Schedule Confirm / Cancel ─────────────────────────────────

@app.post("/api/schedule/confirm/{token}")
async def schedule_confirm(token: str):
    """Apply a pending Logic App schedule. Called by the UI confirmation card."""
    pending = PENDING_SCHEDULE_STORE.pop(token, None)
    if not pending:
        raise HTTPException(status_code=404, detail="Confirmation token not found or already used.")
    if pending.is_expired():
        raise HTTPException(status_code=410, detail="Confirmation token has expired. Ask the agent to preview the schedule again.")

    cfg = get_config()
    if not cfg.logic_app_name or not cfg.logic_app_resource_group:
        raise HTTPException(status_code=503, detail="Logic App not configured on this deployment.")

    subscription_id = cfg.logic_app_subscription_id
    resource_group = cfg.logic_app_resource_group
    logic_app_name = cfg.logic_app_name

    # Build the updated Logic App workflow definition
    definition = {
        "$schema": "https://schema.management.azure.com/providers/Microsoft.Logic/schemas/2016-06-01/workflowdefinition.json#",
        "contentVersion": "1.0.0.0",
        "parameters": {},
        "triggers": {
            "Weekly_Schedule": {
                "type": "Recurrence",
                "recurrence": {
                    "frequency": "Week",
                    "interval": 1,
                    "schedule": {
                        "weekDays": [pending.day_of_week],
                        "hours": [str(pending.hour)],
                        "minutes": [pending.minute],
                    },
                    "timeZone": "GMT Standard Time",
                },
            }
        },
        "actions": {
            "Trigger_MAF_Analysis": {
                "type": "Http",
                "inputs": {
                    "method": "POST",
                    "uri": f"https://maf-multi-agent.yellowcoast-f2115a5b.eastus.azurecontainerapps.io/api/schedule/trigger",
                    "headers": {
                        "Content-Type": "application/json",
                        "X-Schedule-Api-Key": cfg.schedule_api_key,
                    },
                    "body": {},
                },
                "runAfter": {},
            }
        },
        "outputs": {},
    }

    try:
        import asyncio as _asyncio
        from azure.identity import DefaultAzureCredential as _Cred
        import httpx as _httpx

        def _update_logic_app():
            credential = _Cred()
            token_obj = credential.get_token("https://management.azure.com/.default")
            url = (
                f"https://management.azure.com/subscriptions/{subscription_id}"
                f"/resourceGroups/{resource_group}/providers/Microsoft.Logic/workflows"
                f"/{logic_app_name}?api-version=2019-05-01"
            )
            body = {
                "location": "eastus",
                "properties": {"definition": definition, "state": "Enabled"},
            }
            resp = _httpx.put(
                url,
                json=body,
                headers={"Authorization": f"Bearer {token_obj.token}"},
                timeout=30,
            )
            resp.raise_for_status()
            return resp.json()

        await _asyncio.to_thread(_update_logic_app)
    except Exception as exc:
        logger.error("❌ Logic App update failed: %s", exc)
        raise HTTPException(status_code=502, detail=f"Failed to update Logic App schedule: {exc}")

    logger.info(
        "✅ Schedule confirmed: %s at %s every %s → Logic App updated",
        logic_app_name, pending.time_24h, pending.day_of_week,
    )
    return {
        "status": "scheduled",
        "day_of_week": pending.day_of_week,
        "time": pending.human_time,
        "recipients": pending.recipients,
    }


@app.post("/api/schedule/cancel/{token}")
async def schedule_cancel(token: str):
    """Discard a pending schedule without applying it."""
    PENDING_SCHEDULE_STORE.pop(token, None)
    logger.info("🚫 Schedule cancelled: token=%s", token)
    return {"status": "cancelled"}


# ── Fabric Capacity Status ────────────────────────────────────

@app.get("/api/fabric/status")
async def fabric_status():
    """Check Fabric capacity state (Active, Paused, Suspended, etc.)."""
    return await get_fabric_capacity_status()


@app.post("/api/fabric/resume")
async def fabric_resume():
    """Resume a paused/suspended Fabric capacity."""
    return await resume_fabric_capacity()


# ── Session snapshot & history ─────────────────────────────────


def _aggregate_token_usage(events: list[dict], agent_model_map: dict[str, str]) -> dict | None:
    """Aggregate token usage from collected events into a structured breakdown.

    Returns a dict with totals, per-source breakdown (agent + model), and
    token type breakdown (input/output/cached/reasoning), or None if no usage.
    """
    totals = {"input_tokens": 0, "output_tokens": 0, "total_tokens": 0,
              "cached_tokens": 0, "reasoning_tokens": 0}
    by_source: dict[str, dict] = {}

    config = get_config()
    orchestrator_model = config.azure_openai_chat_deployment_name

    for ev in events:
        et = ev.get("event_type", "")
        data = ev.get("data", {})
        source = ev.get("source", "")

        usage = data.get("usage")
        if et == "agent_completed" and usage:
            model = agent_model_map.get(source, "unknown")
            _add_usage(totals, by_source, source, model, usage)

        if et == "workflow_completed":
            if usage:
                _add_usage(totals, by_source, "orchestrator", orchestrator_model, usage)
            # Summary service usage (separate model)
            su = data.get("summary_usage")
            if su:
                summary_model = su.get("model", config.azure_openai_summary_deployment_name)
                _add_usage(totals, by_source, "summary", summary_model, su)

    if totals["total_tokens"] == 0:
        return None

    # Clean up zero values
    for key in ("cached_tokens", "reasoning_tokens"):
        if totals[key] == 0:
            del totals[key]

    return {**totals, "by_source": by_source}


def _add_usage(totals: dict, by_source: dict, source: str, model: str, usage: dict) -> None:
    """Add usage data from one source to the totals and per-source breakdown."""
    inp = usage.get("input_tokens", 0) or 0
    out = usage.get("output_tokens", 0) or 0
    tot = usage.get("total_tokens", 0) or 0
    cached = usage.get("cached_tokens", 0) or 0
    reasoning = usage.get("reasoning_tokens", 0) or 0

    totals["input_tokens"] += inp
    totals["output_tokens"] += out
    totals["total_tokens"] += tot
    totals["cached_tokens"] += cached
    totals["reasoning_tokens"] += reasoning

    if source not in by_source:
        by_source[source] = {"model": model, "input_tokens": 0, "output_tokens": 0,
                             "total_tokens": 0}
    entry = by_source[source]
    entry["input_tokens"] += inp
    entry["output_tokens"] += out
    entry["total_tokens"] += tot
    if cached:
        entry["cached_tokens"] = entry.get("cached_tokens", 0) + cached
    if reasoning:
        entry["reasoning_tokens"] = entry.get("reasoning_tokens", 0) + reasoning

def _build_session_snapshot(
    run_id: str,
    query: str,
    events: list[dict],
    result_text: str,
    document_md: str,
    status: str,
    created_at: str,
    user_email: str | None = None,
) -> dict:
    """Build a complete session snapshot from the current run state."""
    # Derive tasks and documents from collected events
    tasks: list[dict] = []
    documents: list[dict] = []
    agents_seen: dict[str, dict] = {}

    for ev in events:
        et = ev.get("event_type", "")
        data = ev.get("data", {})

        if et == "tasks_created" and data.get("tasks"):
            tasks = data["tasks"]

        if et == "task_completed" and data.get("task_id") is not None:
            tid = data["task_id"]
            for t in tasks:
                if t.get("id") == tid:
                    t["finished"] = True

        if et == "document_updated" and data.get("content"):
            documents.append({
                "version": data.get("version", len(documents) + 1),
                "content": rewrite_sandbox_urls(data["content"]),
                "action": (data.get("history") or {}).get("action", "update"),
            })

        # Track agents
        source = ev.get("source", "")
        if source and source != "orchestrator" and source != "document":
            if source not in agents_seen:
                agents_seen[source] = {"name": source, "display_name": source}

    # Add final document version
    if document_md:
        documents.append({"version": "final", "content": rewrite_sandbox_urls(document_md), "action": "final"})

    # Rewrite sandbox URLs in all collected event text fields
    rewritten_events = []
    for ev in events:
        ev_copy = dict(ev)
        data = ev_copy.get("data", {})
        if isinstance(data, dict):
            data_copy = dict(data)
            for key in ("text", "result", "content", "document"):
                val = data_copy.get(key)
                if isinstance(val, str) and "sandbox:" in val:
                    data_copy[key] = rewrite_sandbox_urls(val)
            ev_copy["data"] = data_copy
        rewritten_events.append(ev_copy)

    # Load agent definitions for the snapshot
    try:
        from src.agent_loader import list_agent_definitions
        agent_defs_raw = list_agent_definitions()
        agent_defs = [
            {"name": a.name, "display_name": a.display_name, "avatar": a.avatar,
             "role": a.role, "model": a.model, "description": a.description}
            for a in agent_defs_raw
        ]
        # Build agent→model mapping for token usage attribution
        agent_model_map = {a.name: a.model for a in agent_defs_raw}
    except (yaml.YAMLError, OSError, ImportError):
        agent_defs = list(agents_seen.values())
        agent_model_map = {}

    # Aggregate token usage from events
    token_usage = _aggregate_token_usage(events, agent_model_map)

    updated_at = datetime.now().isoformat()
    snapshot = {
        "run_id": run_id,
        "user_email": user_email,
        "query": query,
        "timestamp": created_at,
        "updated_at": updated_at,
        "status": status,
        "agents": agent_defs,
        "events": rewritten_events,
        "tasks": tasks,
        "documents": documents,
        "result": rewrite_sandbox_urls(result_text) if result_text else "",
        "stream_label": (
            f"Run {run_id} is still in progress."
            if status == "running"
            else f"Run {run_id} ended with an error."
            if status == "error"
            else f"Replay of run {run_id}"
        ),
    }
    if token_usage:
        snapshot["token_usage"] = token_usage
    return snapshot


async def _persist_session_snapshot(
    user_dir: str,
    run_id: str,
    snapshot: dict,
    include_files: bool = False,
) -> None:
    """Write a session snapshot and, optionally, its sandbox files."""
    history = get_history_store()
    await history.save_session(user_dir, run_id, snapshot)

    if not include_files:
        return

    for filename, (data, _ct) in get_all_files().items():
        if filename:
            try:
                await history.save_file(user_dir, run_id, filename, data)
            except Exception:
                logger.debug("Skipped blob file save for %s", filename)


async def _load_saved_session_for_user(run_id: str, user_email: str | None) -> dict | None:
    """Load a persisted session snapshot scoped to the authenticated user."""
    history = get_history_store()

    if _is_super_user(user_email):
        result = await history.find_session_any_user(run_id)
        return result[1] if result else None

    user_dir = _safe_user_dir(user_email) if user_email else ""
    return await history.get_session(user_dir, run_id)


def _get_output_dir() -> str:
    return os.path.join(os.path.dirname(os.path.dirname(__file__)), "output")


# Regex: only allow alphanumeric, hyphens, underscores (no .. or /)
_SAFE_RUN_ID_RE = re.compile(r"^[a-zA-Z0-9_-]+$")


def _validate_run_id(run_id: str) -> None:
    """Validate run_id to prevent path traversal."""
    if not _SAFE_RUN_ID_RE.match(run_id):
        raise HTTPException(status_code=400, detail="Invalid run_id")


@app.get("/api/history")
async def list_history(request: Request):
    """List saved session snapshots for the authenticated user, newest first."""
    user_email = _require_history_user_email(request)
    history = get_history_store()

    if _is_super_user(user_email):
        return await history.list_all_sessions(include_user=True)

    user_dir = _safe_user_dir(user_email) if user_email else ""
    return await history.list_sessions(user_dir)


@app.get("/api/history/{run_id}")
async def get_history_session(run_id: str, request: Request):
    """Load a complete session snapshot for replay (scoped to authenticated user)."""
    _validate_run_id(run_id)
    snap = await _load_saved_session_for_user(run_id, _require_history_user_email(request))
    if snap is None:
        raise HTTPException(status_code=404, detail="Session not found")
    return snap


@app.delete("/api/history/{run_id}")
async def delete_history_session(run_id: str, request: Request):
    """Delete a saved session (scoped to authenticated user)."""
    _validate_run_id(run_id)
    user_email = _require_history_user_email(request)
    history = get_history_store()

    if _is_super_user(user_email):
        result = await history.find_session_any_user(run_id)
        if not result:
            raise HTTPException(status_code=404, detail="Session not found")
        user_dir = result[0]
    else:
        user_dir = _safe_user_dir(user_email) if user_email else ""

    deleted = await history.delete_session(user_dir, run_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Session not found")
    return {"deleted": run_id}


def setup_logging():
    """Configure logging for API server."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
        datefmt="%H:%M:%S",
    )
    for noisy in [
        "azure.core.pipeline.policies.http_logging_policy",
        "azure.identity",
        "azure.monitor.opentelemetry.exporter",
        "httpx",
        "openai",
    ]:
        logging.getLogger(noisy).setLevel(logging.WARNING)


if __name__ == "__main__":
    import uvicorn
    setup_logging()
    uvicorn.run(app, host="0.0.0.0", port=8000)
