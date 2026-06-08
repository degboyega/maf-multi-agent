"use client";

import { FormEvent, useRef, useEffect } from "react";
import { LoaderCircle, Send, RotateCcw } from "lucide-react";

export type ReasoningEffort = "high" | "medium" | "low" | "none";

const REASONING_OPTIONS: { value: ReasoningEffort; label: string; hint: string }[] = [
  { value: "low", label: "Low", hint: "Fast" },
  { value: "medium", label: "Med", hint: "Balanced" },
  { value: "high", label: "High", hint: "Best quality" },
];

interface QueryComposerProps {
  disabled: boolean;
  onQueryChange: (query: string) => void;
  query: string;
  onRun: (query: string) => void;
  reasoningEffort: ReasoningEffort;
  onReasoningEffortChange: (effort: ReasoningEffort) => void;
  conversationTurn: number;
  onNewConversation: () => void;
}

export function QueryComposer({
  disabled,
  onQueryChange,
  query,
  onRun,
  reasoningEffort,
  onReasoningEffortChange,
  conversationTurn,
  onNewConversation,
}: QueryComposerProps) {
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  // Auto-focus after a response completes so user can type immediately
  useEffect(() => {
    if (!disabled) {
      textareaRef.current?.focus();
    }
  }, [disabled]);

  const handleSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const trimmed = query.trim();
    if (!trimmed || disabled) return;
    onRun(trimmed);
  };

  const handleKeyDown = (event: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      const trimmed = query.trim();
      if (trimmed && !disabled) onRun(trimmed);
    }
  };

  return (
    <div className="chat-input-shell">
      {conversationTurn > 0 && (
        <div className="chat-conversation-bar">
          <span className="chat-conversation-label">
            Turn {conversationTurn} · Conversation active
          </span>
          <button
            type="button"
            className="chat-new-conversation-button"
            onClick={onNewConversation}
            title="Clear conversation and start fresh"
          >
            <RotateCcw className="h-3 w-3" />
            New conversation
          </button>
        </div>
      )}

      <form onSubmit={handleSubmit} className="chat-input-form">
        <textarea
          ref={textareaRef}
          value={query}
          onChange={(e) => onQueryChange(e.target.value)}
          onKeyDown={handleKeyDown}
          disabled={disabled}
          rows={2}
          className="chat-textarea"
          placeholder={
            conversationTurn > 0
              ? "Follow up, ask for more detail, or say 'email this to the team'…"
              : "Describe what you want the agent system to do…"
          }
        />

        <div className="chat-input-actions">
          <div className="chat-reasoning-group">
            <span className="chat-reasoning-label">Reasoning</span>
            <div className="reasoning-toggle-group">
              {REASONING_OPTIONS.map((opt) => (
                <button
                  key={opt.value}
                  type="button"
                  title={opt.hint}
                  disabled={disabled}
                  aria-pressed={reasoningEffort === opt.value}
                  onClick={() => onReasoningEffortChange(opt.value)}
                  className={`reasoning-toggle-button ${
                    reasoningEffort === opt.value ? "reasoning-toggle-button-active" : ""
                  }`}
                >
                  {opt.label}
                </button>
              ))}
            </div>
          </div>

          <button
            type="submit"
            disabled={disabled || !query.trim()}
            className="action-button chat-send-button"
          >
            {disabled ? (
              <LoaderCircle className="h-4 w-4 animate-spin" />
            ) : (
              <Send className="h-4 w-4" />
            )}
            {disabled ? "Running…" : "Send"}
          </button>
        </div>
      </form>
    </div>
  );
}
