"""MailTools — facilitator tools for sending email to the user and/or team."""

import logging

from agent_framework import FunctionTool
from pydantic import BaseModel, Field

from src.config import Config
from src.graph_mail_client import send_mail

logger = logging.getLogger(__name__)


class SendEmailInput(BaseModel):
    subject: str = Field(description="Email subject line — short summary of the request/response.")
    body: str = Field(description="Email body in HTML format with the full final response content.")


class MailTools:
    """Facilitator tools for sending email via Microsoft Graph.

    Sends from the configured sender mailbox (MAIL_SENDER_ADDRESS) using
    Managed Identity with Mail.Send permission.

    Two tools are exposed:
    - send_email_to_me: sends only to the logged-in user
    - send_email_to_team: sends to the logged-in user and CCs the full team
      (configured via MAIL_TEAM_ADDRESSES, comma-separated)
    """

    def __init__(self, user_email: str, config: Config):
        self._user_email = user_email
        self._sender = config.mail_sender_address
        self._team_addresses = [
            a.strip()
            for a in config.mail_team_addresses.split(",")
            if a.strip()
        ]

    async def _send_email_to_user(self, subject: str, body: str) -> str:
        """Send an email to the logged-in user only."""
        if not self._user_email:
            return "Error: no user email available — cannot send email."
        if not self._sender:
            return "Error: MAIL_SENDER_ADDRESS not configured — cannot send email."

        logger.info("📧 MailTools.send_to_me: to=%s subject='%s'", self._user_email, subject[:80])
        return await send_mail(
            sender=self._sender,
            to=self._user_email,
            subject=subject,
            body_html=body,
        )

    async def _send_email_to_team(self, subject: str, body: str) -> str:
        """Send an email to the logged-in user and CC the full team."""
        if not self._user_email:
            return "Error: no user email available — cannot send email."
        if not self._sender:
            return "Error: MAIL_SENDER_ADDRESS not configured — cannot send email."
        if not self._team_addresses:
            return "Error: MAIL_TEAM_ADDRESSES not configured — cannot CC the team."

        logger.info(
            "📧 MailTools.send_to_team: to=%s cc=%s subject='%s'",
            self._user_email, self._team_addresses, subject[:80],
        )
        return await send_mail(
            sender=self._sender,
            to=self._user_email,
            subject=subject,
            body_html=body,
            cc=self._team_addresses,
        )

    def get_tools(self) -> list[FunctionTool]:
        """Return mail FunctionTool objects for the facilitator."""
        tools = [
            FunctionTool(
                name="send_email_to_me",
                description=(
                    f"Send an email with the final response to just the logged-in user "
                    f"({self._user_email}). Use when the user says 'email me' or 'send it to me'."
                ),
                func=self._send_email_to_user,
                input_model=SendEmailInput,
            ),
        ]

        if self._team_addresses:
            team_list = ", ".join(self._team_addresses)
            tools.append(
                FunctionTool(
                    name="send_email_to_team",
                    description=(
                        f"Send an email to the logged-in user ({self._user_email}) "
                        f"and CC the full team ({team_list}). "
                        f"Use when the user says 'email the team', 'CC everyone', or names team members."
                    ),
                    func=self._send_email_to_team,
                    input_model=SendEmailInput,
                )
            )

        return tools
