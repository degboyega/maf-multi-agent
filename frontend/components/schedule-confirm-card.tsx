"use client";

import { useState } from "react";
import { Calendar, Check, X } from "lucide-react";

interface ScheduleConfirmCardProps {
  token: string;
  dayOfWeek: string;
  humanTime: string;
  recipients: string[];
  onDismiss: () => void;
}

type CardState = "idle" | "saving" | "saved" | "cancelled" | "error";

export function ScheduleConfirmCard({
  token,
  dayOfWeek,
  humanTime,
  recipients,
  onDismiss,
}: ScheduleConfirmCardProps) {
  const [state, setState] = useState<CardState>("idle");
  const [errorMsg, setErrorMsg] = useState("");

  const handleConfirm = async () => {
    setState("saving");
    try {
      const res = await fetch(`/api/schedule/confirm/${encodeURIComponent(token)}`, { method: "POST" });
      if (res.ok) {
        setState("saved");
        setTimeout(onDismiss, 2500);
      } else {
        const body = await res.json().catch(() => ({}));
        setErrorMsg((body as { detail?: string }).detail || `HTTP ${res.status}`);
        setState("error");
      }
    } catch {
      setErrorMsg("Could not reach the backend.");
      setState("error");
    }
  };

  const handleCancel = async () => {
    setState("cancelled");
    await fetch(`/api/schedule/cancel/${encodeURIComponent(token)}`, { method: "POST" }).catch(() => {});
    setTimeout(onDismiss, 1000);
  };

  return (
    <div className="schedule-confirm-card">
      <div className="schedule-confirm-header">
        <span className="schedule-confirm-icon">
          <Calendar className="h-4 w-4" />
        </span>
        <span className="schedule-confirm-title">Set up weekly schedule</span>
        {state === "idle" && (
          <button type="button" className="email-confirm-close" onClick={handleCancel} aria-label="Dismiss">
            <X className="h-3.5 w-3.5" />
          </button>
        )}
      </div>

      <div className="schedule-confirm-meta">
        <div className="email-confirm-row">
          <span className="email-confirm-label">Runs</span>
          <span className="email-confirm-value">Every {dayOfWeek} at {humanTime}</span>
        </div>
        <div className="email-confirm-row">
          <span className="email-confirm-label">Sends to</span>
          <span className="email-confirm-value">{recipients.join(", ")}</span>
        </div>
      </div>

      <p className="schedule-confirm-note">
        This will update the Logic App — the first report runs next {dayOfWeek}.
      </p>

      {state === "saved" && (
        <p className="email-confirm-status email-confirm-status-sent">Schedule applied. Next run: {dayOfWeek} at {humanTime}.</p>
      )}
      {state === "cancelled" && (
        <p className="email-confirm-status email-confirm-status-cancelled">Cancelled.</p>
      )}
      {state === "error" && (
        <p className="email-confirm-status email-confirm-status-error">Failed: {errorMsg}</p>
      )}

      {state === "idle" && (
        <div className="email-confirm-actions">
          <button type="button" className="secondary-button" onClick={handleCancel}>
            Cancel
          </button>
          <button type="button" className="action-button" onClick={handleConfirm}>
            <Check className="h-3.5 w-3.5" />
            Confirm schedule
          </button>
        </div>
      )}

      {state === "saving" && (
        <div className="email-confirm-actions">
          <button type="button" className="action-button" disabled>
            Applying…
          </button>
        </div>
      )}
    </div>
  );
}
