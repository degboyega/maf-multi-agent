import { PlannerShell } from "@/components/planner-shell";
import { ErrorBoundary } from "@/components/error-boundary";

export default function ChatPage() {
  return (
    <ErrorBoundary>
      <PlannerShell />
    </ErrorBoundary>
  );
}
