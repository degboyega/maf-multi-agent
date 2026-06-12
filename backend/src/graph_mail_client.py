"""Mail client — sends via SMTP (username/password) or Microsoft Graph (managed identity).

Priority:
  1. SMTP  — when MAIL_SENDER_PASSWORD is set (no admin permission grant needed)
  2. Graph — when only managed identity / DefaultAzureCredential is available
"""

import asyncio
import logging
import os
import smtplib
import threading
import time
from dataclasses import dataclass
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Optional

import httpx
from azure.identity import DefaultAzureCredential

logger = logging.getLogger(__name__)

GRAPH_SCOPE = "https://graph.microsoft.com/.default"
GRAPH_SEND_MAIL_URL = "https://graph.microsoft.com/v1.0/users/{sender}/sendMail"
SMTP_HOST = "smtp.office365.com"
SMTP_PORT = 587
TOKEN_REFRESH_BUFFER_SECONDS = 300


@dataclass
class _CachedToken:
    token: str
    expires_at: float


_token_cache: dict[str, _CachedToken] = {}
_token_lock = threading.Lock()
_credential: Optional[DefaultAzureCredential] = None


def _get_graph_token() -> str:
    global _credential
    cache_key = f"graph:{GRAPH_SCOPE}"
    with _token_lock:
        cached = _token_cache.get(cache_key)
        if cached and cached.expires_at > time.time() + TOKEN_REFRESH_BUFFER_SECONDS:
            return cached.token

        if _credential is None:
            managed_identity_client_id = os.environ.get("AZURE_CLIENT_ID", "")
            if managed_identity_client_id:
                _credential = DefaultAzureCredential(
                    managed_identity_client_id=managed_identity_client_id,
                )
                logger.info("🔑 Graph mail: using MI client_id=%s...", managed_identity_client_id[:8])
            else:
                _credential = DefaultAzureCredential()
                logger.info("🔑 Graph mail: using DefaultAzureCredential (auto-resolve)")

        token_response = _credential.get_token(GRAPH_SCOPE)
        _token_cache[cache_key] = _CachedToken(
            token=token_response.token,
            expires_at=token_response.expires_on,
        )
        logger.info(
            "🔑 Graph token acquired (expires in %.0fs)",
            token_response.expires_on - time.time(),
        )
        return token_response.token




async def send_mail(
    sender: str,
    to: str,
    subject: str,
    body_html: str,
    cc: list[str] | None = None,
    attachments: list[dict] | None = None,
) -> str:
    """Send an email via SMTP or Graph API.

    attachments: list of {"name": str, "content_type": str, "data": bytes}
    """
    import base64

    all_recipients = [to] + (cc or [])
    recipients_str = ", ".join(all_recipients)
    cc_str = f", cc={cc}" if cc else ""
    attach_str = f", {len(attachments)} attachment(s)" if attachments else ""

    password = os.environ.get("MAIL_SENDER_PASSWORD", "")
    if password:
        logger.info("📧 Sending email (SMTP): from=%s to=%s%s subject='%s'%s", sender, to, cc_str, subject[:80], attach_str)
        try:
            await asyncio.to_thread(_smtp_send_with_attachments, sender, password, to, subject, body_html, cc, attachments)
            logger.info("✅ Email sent (SMTP) to %s", recipients_str)
            return f"Email sent successfully to {recipients_str}"
        except smtplib.SMTPAuthenticationError:
            logger.error("❌ SMTP auth failed for %s", sender)
            return (
                "Failed to send email: SMTP authentication failed. "
                "Check MAIL_SENDER_PASSWORD or ask your admin to enable SMTP AUTH for the mailbox."
            )
        except Exception as exc:
            logger.error("❌ SMTP send failed: %s", exc)
            return f"Failed to send email: {exc}"

    # Fall back to Graph API via managed identity
    logger.info("📧 Sending email (Graph): from=%s to=%s%s subject='%s'%s", sender, to, cc_str, subject[:80], attach_str)
    try:
        token = await asyncio.to_thread(_get_graph_token)
    except Exception as exc:
        logger.error("❌ Failed to acquire Graph token: %s", exc)
        return f"Failed to send email: could not acquire Graph token — {exc}"

    url = GRAPH_SEND_MAIL_URL.format(sender=sender)
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }
    message: dict = {
        "subject": subject,
        "body": {"contentType": "HTML", "content": body_html},
        "toRecipients": [{"emailAddress": {"address": to}}],
    }
    if cc:
        message["ccRecipients"] = [{"emailAddress": {"address": a}} for a in cc]

    if attachments:
        message["attachments"] = [
            {
                "@odata.type": "#microsoft.graph.fileAttachment",
                "name": att["name"],
                "contentType": att["content_type"],
                "contentBytes": base64.b64encode(att["data"]).decode("ascii"),
            }
            for att in attachments
            if att.get("data")
        ]

    payload = {"message": message, "saveToSentItems": "true"}

    async with httpx.AsyncClient(timeout=60.0) as client:
        resp = await client.post(url, headers=headers, json=payload)

    if resp.status_code == 202:
        logger.info("✅ Email sent (Graph) to %s%s", recipients_str, attach_str)
        return f"Email sent successfully to {recipients_str}"
    else:
        error_text = resp.text[:500]
        logger.error("❌ Graph sendMail failed: %d %s", resp.status_code, error_text)
        return f"Failed to send email (HTTP {resp.status_code}): {error_text}"


def _smtp_send_with_attachments(
    sender: str,
    password: str,
    to: str,
    subject: str,
    body_html: str,
    cc: list[str] | None,
    attachments: list[dict] | None,
) -> None:
    from email.mime.base import MIMEBase
    from email import encoders

    msg = MIMEMultipart("mixed")
    msg["Subject"] = subject
    msg["From"] = sender
    msg["To"] = to
    if cc:
        msg["Cc"] = ", ".join(cc)

    alt = MIMEMultipart("alternative")
    alt.attach(MIMEText(body_html, "html"))
    msg.attach(alt)

    for att in (attachments or []):
        if not att.get("data"):
            continue
        part = MIMEBase("application", "octet-stream")
        part.set_payload(att["data"])
        encoders.encode_base64(part)
        part.add_header("Content-Disposition", f'attachment; filename="{att["name"]}"')
        part.add_header("Content-Type", att.get("content_type", "application/octet-stream"))
        msg.attach(part)

    with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
        server.ehlo()
        server.starttls()
        server.login(sender, password)
        recipients = [to] + (cc or [])
        server.sendmail(sender, recipients, msg.as_string())
