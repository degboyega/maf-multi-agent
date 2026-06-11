export interface StarterPrompt {
  title: string;
  pill: string;
  icon: string;
  query: string;
}

export const STARTER_PROMPTS: StarterPrompt[] = [
  {
    title: "Full compressor health check",
    pill: "Analyse both compressors",
    icon: "Activity",
    query:
      "Carry out a full health analysis on both COMP-001 (Houston, TX) and COMP-002 (Midland, TX). For each asset retrieve the last 7 days of sensor readings, identify any parameters that breach or approach the advisory thresholds defined in the Emerson CSER2000 maintenance manual and the Iqbal guidelines, cross-reference against the maintenance history to identify recurring issues, and assess overall risk. Summarise your findings in a structured report with a status for each asset (Normal / Advisory / Critical), specific readings that triggered concern, root cause hypothesis, and recommended action with urgency rating.",
  },
  {
    title: "COMP-001 status",
    pill: "COMP-001 health status",
    icon: "Gauge",
    query:
      "Assess the current health of COMP-001 in Houston, TX. Pull the latest sensor readings, check them against the Emerson CSER2000 advisory and alarm thresholds, review any open maintenance actions, and give me a clear status: Normal, Advisory, or Critical — with the specific readings that triggered the assessment.",
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
      "Run a full health analysis on COMP-001 and COMP-002, then prepare a structured maintenance report and send it to the engineering team for review.",
  },
  {
    title: "Schedule weekly report",
    pill: "Schedule weekly analysis",
    icon: "Calendar",
    query:
      "I want to schedule an automated weekly health report for COMP-001 and COMP-002. Ask me what day and time I want it, what I want it to cover, and confirm the details before setting it up.",
  },
];
