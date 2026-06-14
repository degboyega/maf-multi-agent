export interface StarterPrompt {
  title: string;
  pill: string;
  icon: string;
  query: string;
}

export const STARTER_PROMPTS: StarterPrompt[] = [
  {
    title: "Full diagnostic — all 4 agents",
    pill: "Full diagnostic report",
    icon: "Activity",
    query:
      "Give me a full diagnostic report on COMP-001 and COMP-002 for the last 7 days. I need: (1) the latest sensor readings with any threshold breaches flagged against the Emerson CSER2000 manual, (2) a line chart showing discharge temperature and vibration trends over the week, (3) what the Iqbal maintenance guidelines say about the fault pattern we're seeing, and (4) any recent industry advisories or weather conditions in the Niger Delta that could be contributing to the anomaly. Summarise with a risk rating and recommended next action.",
  },
  {
    title: "COMP-001 status",
    pill: "COMP-001 health status",
    icon: "Gauge",
    query:
      "Assess the current health of COMP-001 in Warri, Delta State. Pull the latest sensor readings, check them against the Emerson CSER2000 advisory and alarm thresholds, review any open maintenance actions, and give me a clear status: Normal, Advisory, or Critical — with the specific readings that triggered the assessment.",
  },
  {
    title: "Last 7 days faults",
    pill: "Fault history — last 7 days",
    icon: "AlertTriangle",
    query:
      "Review the maintenance history and sensor data for COMP-001 and COMP-002 over the last 7 days. List any fault events, anomalies, or threshold breaches that occurred, which asset was affected, what the likely cause was, and whether there is a recurring pattern that needs attention.",
  },
  {
    title: "Send report to team",
    pill: "Send health report to team",
    icon: "Mail",
    query:
      "Run a full health analysis on COMP-001 (Warri, Delta State) and COMP-002 (Eket, Akwa Ibom), then prepare a structured maintenance report and send it to the engineering team for review.",
  },
  {
    title: "Schedule weekly report",
    pill: "Schedule weekly analysis",
    icon: "Calendar",
    query:
      "I want to schedule an automated weekly health report for COMP-001 and COMP-002. Ask me what day and time I want it, what I want it to cover, and confirm the details before setting it up.",
  },
];
