"""MailTools — facilitator tool for previewing email before user confirms sending."""

import logging
import re
import secrets
import time
from dataclasses import dataclass, field
from typing import Optional

from agent_framework import FunctionTool
from pydantic import BaseModel, Field

from src.config import Config
from src.events import AgentEvent, EventCallback, EventType
from src.scratchpad.pptx_builder import build_health_report_pptx

logger = logging.getLogger(__name__)

TOKEN_TTL_SECONDS = 300  # tokens expire after 5 minutes


@dataclass
class PendingMail:
    token: str
    subject: str
    body: str
    recipient_type: str  # "me" | "team"
    sender: str
    user_email: str
    team_addresses: list[str] = field(default_factory=list)
    pptx_bytes: Optional[bytes] = None
    created_at: float = field(default_factory=time.time)

    def is_expired(self) -> bool:
        return time.time() - self.created_at > TOKEN_TTL_SECONDS


# Module-level store — imported by api.py for the confirm/cancel endpoints
PENDING_MAIL_STORE: dict[str, PendingMail] = {}


class PreviewEmailInput(BaseModel):
    subject: str = Field(description="Email subject line — short summary of the content.")
    body: str = Field(description="Full email body in HTML format.")
    recipient_type: str = Field(
        description=(
            "Who to send to. Use 'me' to send only to the logged-in user, "
            "or 'team' to send to the user and CC the full team."
        )
    )


class MailTools:
    """Facilitator tool for email previewing.

    Replaces the old send_email_to_me / send_email_to_team tools with a single
    preview_email tool. The agent calls preview_email to stage the email and
    emit an email_pending_confirmation SSE event. Actual sending only happens
    when the user clicks Send in the UI, which calls POST /api/mail/confirm/{token}.
    """

    def __init__(self, user_email: str, config: Config, event_callback: EventCallback = None):
        self._user_email = user_email
        self._sender = config.mail_sender_address
        self._team_addresses = [
            a.strip()
            for a in config.mail_team_addresses.split(",")
            if a.strip()
        ]
        self._event_callback = event_callback

    async def _preview_email(self, subject: str, body: str, recipient_type: str) -> str:
        if not self._user_email:
            return "Error: no user email available — cannot preview email."
        if not self._sender:
            return "Error: MAIL_SENDER_ADDRESS not configured — cannot preview email."

        recipient_type = recipient_type.strip().lower()
        if recipient_type not in ("me", "team"):
            recipient_type = "me"

        if recipient_type == "team" and not self._team_addresses:
            return "Error: MAIL_TEAM_ADDRESSES not configured — cannot send to team."

        # Build PPTX attachment from the email body
        pptx_bytes = build_health_report_pptx(body, subject)

        token = secrets.token_urlsafe(16)
        pending = PendingMail(
            token=token,
            subject=subject,
            body=body,
            recipient_type=recipient_type,
            sender=self._sender,
            user_email=self._user_email,
            team_addresses=self._team_addresses if recipient_type == "team" else [],
            pptx_bytes=pptx_bytes,
        )
        PENDING_MAIL_STORE[token] = pending

        cc = self._team_addresses if recipient_type == "team" else []
        body_preview = re.sub(r"<[^>]+>", "", body)[:300].strip()

        logger.info(
            "📧 MailTools.preview: token=%s to=%s cc=%s subject='%s'",
            token, self._user_email, cc, subject[:80],
        )

        if self._event_callback:
            self._event_callback(AgentEvent(
                event_type=EventType.EMAIL_PENDING_CONFIRMATION,
                source="orchestrator",
                data={
                    "mail_token": token,
                    "mail_subject": subject,
                    "mail_to": self._user_email,
                    "mail_cc": cc,
                    "mail_body_preview": body_preview,
                },
            ))

        cc_desc = f" and CC {len(cc)} team members" if cc else ""
        return (
            f"Email preview ready. Subject: '{subject}'. "
            f"Will send to {self._user_email}{cc_desc}. "
            f"Waiting for user confirmation in the interface — do not call preview_email again."
        )

    def get_tools(self) -> list[FunctionTool]:
        team_note = (
            f" Use recipient_type='team' to also CC {', '.join(self._team_addresses)}."
            if self._team_addresses
            else ""
        )
        return [
            FunctionTool(
                name="preview_email",
                description=(
                    f"Stage an email for the user to review before it is sent. "
                    f"The user ({self._user_email}) will see a confirmation card and must click Send. "
                    f"Use recipient_type='me' to send only to the logged-in user."
                    f"{team_note}"
                    f" Always call this tool instead of sending directly."
                ),
                func=self._preview_email,
                input_model=PreviewEmailInput,
            )
        ]
