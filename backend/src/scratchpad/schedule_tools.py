"""ScheduleTools — agent tool for setting up recurring report schedules via Logic Apps."""

import logging
import secrets
import time
from dataclasses import dataclass, field

from agent_framework import FunctionTool
from pydantic import BaseModel, Field

from src.config import Config
from src.events import AgentEvent, EventCallback, EventType

logger = logging.getLogger(__name__)

TOKEN_TTL_SECONDS = 600  # 10 minutes to confirm

DAYS_OF_WEEK = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]


@dataclass
class PendingSchedule:
    token: str
    day_of_week: str       # e.g. "Wednesday"
    time_24h: str          # e.g. "08:00"
    recipient_type: str    # "me" | "team"
    user_email: str
    team_addresses: list[str] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)

    def is_expired(self) -> bool:
        return time.time() - self.created_at > TOKEN_TTL_SECONDS

    @property
    def hour(self) -> int:
        return int(self.time_24h.split(":")[0])

    @property
    def minute(self) -> int:
        return int(self.time_24h.split(":")[1]) if ":" in self.time_24h else 0

    @property
    def human_time(self) -> str:
        h, m = self.hour, self.minute
        period = "AM" if h < 12 else "PM"
        display_h = h if h <= 12 else h - 12
        display_h = 12 if display_h == 0 else display_h
        return f"{display_h}:{m:02d} {period}"

    @property
    def recipients(self) -> list[str]:
        if self.recipient_type == "team":
            return [self.user_email] + self.team_addresses
        return [self.user_email]


# Module-level store — imported by api.py for confirm/cancel endpoints
PENDING_SCHEDULE_STORE: dict[str, PendingSchedule] = {}


class PreviewScheduleInput(BaseModel):
    day_of_week: str = Field(
        description=(
            "Day of the week for the recurring report. "
            "One of: Monday, Tuesday, Wednesday, Thursday, Friday, Saturday, Sunday."
        )
    )
    time_24h: str = Field(
        description=(
            "Time to run in 24-hour HH:MM format. "
            "Interpret natural language: 'morning' = 08:00, 'afternoon' = 14:00, "
            "'evening' = 18:00, 'end of day' = 17:00."
        )
    )
    recipient_type: str = Field(
        description=(
            "Who receives the report: 'me' to send only to the logged-in user, "
            "'team' to send to the user and CC the full engineering team."
        )
    )


class ScheduleTools:
    """Agent tool for scheduling recurring reports.

    The agent calls preview_schedule to stage a schedule change and emit
    a schedule_pending_confirmation event. The actual Logic App update only
    happens when the user clicks Confirm in the UI.
    """

    def __init__(self, user_email: str, config: Config, event_callback: EventCallback = None):
        self._user_email = user_email
        self._team_addresses = [
            a.strip()
            for a in config.mail_team_addresses.split(",")
            if a.strip()
        ]
        self._schedule_enabled = bool(config.logic_app_name and config.logic_app_resource_group)
        self._event_callback = event_callback

    async def _preview_schedule(self, day_of_week: str, time_24h: str, recipient_type: str) -> str:
        if not self._schedule_enabled:
            return "Error: scheduling is not configured on this deployment."
        if not self._user_email:
            return "Error: no user email available — cannot set up schedule."

        # Normalise day
        day = day_of_week.strip().capitalize()
        if day not in DAYS_OF_WEEK:
            return f"Error: '{day_of_week}' is not a valid day. Use one of: {', '.join(DAYS_OF_WEEK)}."

        # Normalise time
        t = time_24h.strip()
        try:
            parts = t.split(":")
            hour = int(parts[0])
            minute = int(parts[1]) if len(parts) > 1 else 0
            if not (0 <= hour <= 23 and 0 <= minute <= 59):
                raise ValueError
            normalised_time = f"{hour:02d}:{minute:02d}"
        except (ValueError, IndexError):
            return f"Error: '{time_24h}' is not a valid time. Use HH:MM format, e.g. '08:00'."

        recipient_type = recipient_type.strip().lower()
        if recipient_type not in ("me", "team"):
            recipient_type = "me"

        if recipient_type == "team" and not self._team_addresses:
            return "Error: MAIL_TEAM_ADDRESSES not configured — cannot send to team."

        token = secrets.token_urlsafe(16)
        pending = PendingSchedule(
            token=token,
            day_of_week=day,
            time_24h=normalised_time,
            recipient_type=recipient_type,
            user_email=self._user_email,
            team_addresses=self._team_addresses if recipient_type == "team" else [],
        )
        PENDING_SCHEDULE_STORE[token] = pending

        logger.info(
            "📅 ScheduleTools.preview: token=%s day=%s time=%s recipient=%s to=%s",
            token, day, normalised_time, recipient_type, pending.recipients,
        )

        if self._event_callback:
            self._event_callback(AgentEvent(
                event_type=EventType.SCHEDULE_PENDING_CONFIRMATION,
                source="orchestrator",
                data={
                    "schedule_token": token,
                    "day_of_week": day,
                    "time_24h": normalised_time,
                    "human_time": pending.human_time,
                    "recipient_type": recipient_type,
                    "recipients": pending.recipients,
                },
            ))

        recipients_desc = (
            f"{self._user_email} and {len(self._team_addresses)} team member(s)"
            if recipient_type == "team"
            else self._user_email
        )
        return (
            f"Schedule preview ready. Weekly report will run every {day} at {pending.human_time}, "
            f"sent to {recipients_desc}. "
            f"Waiting for user confirmation in the interface — do not call preview_schedule again."
        )

    def get_tools(self) -> list[FunctionTool]:
        team_note = (
            f" Use recipient_type='team' to also CC {', '.join(self._team_addresses)}."
            if self._team_addresses
            else ""
        )
        return [
            FunctionTool(
                name="preview_schedule",
                description=(
                    f"Set up a recurring weekly report schedule. The user ({self._user_email}) "
                    f"will see a confirmation card showing exactly when the report will run and who "
                    f"it will be sent to. They must click Confirm before the schedule is applied. "
                    f"Use this when the user asks to schedule, automate, or set up a recurring report."
                    f"{team_note}"
                ),
                func=self._preview_schedule,
                input_model=PreviewScheduleInput,
            )
        ]
