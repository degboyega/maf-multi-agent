"use client";

import { useState } from "react";
import { Mail, Send, X } from "lucide-react";

interface EmailConfirmCardProps {
  token: string;
  subject: string;
  to: string;
  cc: string[];
  bodyPreview: string;
  onDismiss: () => void;
}

type CardState = "idle" | "sending" | "sent" | "cancelled" | "error";

export function EmailConfirmCard({ token, subject, to, cc, bodyPreview, onDismiss }: EmailConfirmCardProps) {
  const [state, setState] = useState<CardState>("idle");
  const [errorMsg, setErrorMsg] = useState("");

  const handleConfirm = async () => {
    setState("sending");
    try {
      const res = await fetch(`/api/mail/confirm/${encodeURIComponent(token)}`, { method: "POST" });
      if (res.ok) {
        setState("sent");
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
    await fetch(`/api/mail/cancel/${encodeURIComponent(token)}`, { method: "POST" }).catch(() => {});
    setTimeout(onDismiss, 1000);
  };

  return (
    <div className="email-confirm-card">
      <div className="email-confirm-header">
        <span className="email-confirm-icon">
          <Mail className="h-4 w-4" />
        </span>
        <span className="email-confirm-title">Ready to send</span>
        {state === "idle" && (
          <button type="button" className="email-confirm-close" onClick={handleCancel} aria-label="Dismiss">
            <X className="h-3.5 w-3.5" />
          </button>
        )}
      </div>

      <div className="email-confirm-meta">
        <div className="email-confirm-row">
          <span className="email-confirm-label">Subject</span>
          <span className="email-confirm-value">{subject}</span>
        </div>
        <div className="email-confirm-row">
          <span className="email-confirm-label">To</span>
          <span className="email-confirm-value">{to}</span>
        </div>
        {cc.length > 0 && (
          <div className="email-confirm-row">
            <span className="email-confirm-label">CC</span>
            <span className="email-confirm-value">{cc.join(", ")}</span>
          </div>
        )}
      </div>

      {bodyPreview && (
        <div className="email-confirm-preview">
          <p className="email-confirm-preview-text">{bodyPreview}&hellip;</p>
        </div>
      )}

      {state === "sent" && (
        <p className="email-confirm-status email-confirm-status-sent">Email sent successfully.</p>
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
            <Send className="h-3.5 w-3.5" />
            Send email
          </button>
        </div>
      )}

      {state === "sending" && (
        <div className="email-confirm-actions">
          <button type="button" className="action-button" disabled>
            Sending…
          </button>
        </div>
      )}
    </div>
  );
}
