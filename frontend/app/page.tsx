import Link from "next/link";
import { Bot, BrainCircuit, Calendar, ChevronRight, Mail, Settings2, Zap } from "lucide-react";

export default function LandingPage() {
  return (
    <div className="landing-root">

      {/* ── Nav ── */}
      <nav className="landing-nav">
        <div className="landing-nav-inner">
          <div className="landing-nav-brand">
            <span className="landing-nav-spark">✦</span>
            <span className="landing-nav-name">MAF</span>
          </div>
          <Link href="/chat" className="landing-launch-btn">
            Launch Platform <ChevronRight className="h-4 w-4" />
          </Link>
        </div>
      </nav>

      {/* ── Hero ── */}
      <section className="landing-hero">
        <div className="landing-hero-inner">
          <div className="landing-hero-badge">
            <span className="landing-badge-dot" />
            Multi-Agentic AI Framework
          </div>

          <h1 className="landing-hero-title">
            Autonomous compressor
            <br />
            <span className="landing-hero-accent">intelligence</span> for O&amp;G
          </h1>

          <p className="landing-hero-sub">
            Multi-agent AI that monitors sensor data, reasons against OEM thresholds,
            cross-references maintenance history, and delivers structured reports to your
            engineering team — automatically, every week.
          </p>

          <div className="landing-hero-cta">
            <Link href="/chat" className="landing-primary-btn">
              Launch Platform <ChevronRight className="h-4 w-4" />
            </Link>
            <span className="landing-hero-meta">Built on Microsoft Azure AI Foundry</span>
          </div>
        </div>

        {/* Floating asset status cards */}
        <div className="landing-asset-cards">
          <div className="landing-asset-card">
            <div className="landing-asset-header">
              <span className="landing-asset-id">COMP-001</span>
              <span className="landing-status-pill landing-status-advisory">Advisory</span>
            </div>
            <div className="landing-asset-location">Warri, Delta State</div>
            <div className="landing-asset-metrics">
              <div className="landing-metric">
                <span className="landing-metric-label">Discharge Temp</span>
                <span className="landing-metric-value warning">187°F</span>
              </div>
              <div className="landing-metric">
                <span className="landing-metric-label">Vibration</span>
                <span className="landing-metric-value">0.18 in/s</span>
              </div>
            </div>
          </div>

          <div className="landing-asset-card">
            <div className="landing-asset-header">
              <span className="landing-asset-id">COMP-002</span>
              <span className="landing-status-pill landing-status-normal">Normal</span>
            </div>
            <div className="landing-asset-location">Eket, Akwa Ibom</div>
            <div className="landing-asset-metrics">
              <div className="landing-metric">
                <span className="landing-metric-label">Discharge Temp</span>
                <span className="landing-metric-value">162°F</span>
              </div>
              <div className="landing-metric">
                <span className="landing-metric-label">Vibration</span>
                <span className="landing-metric-value">0.11 in/s</span>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* ── How It Works ── */}
      <section className="landing-section">
        <div className="landing-section-inner">
          <p className="landing-eyebrow">How it works</p>
          <h2 className="landing-section-title">Five steps. Zero manual effort.</h2>

          <div className="landing-steps">
            {[
              { n: "01", icon: Calendar, title: "Schedule triggers", body: "Azure Logic App fires automatically on the schedule you set — daily, weekly, or on-demand." },
              { n: "02", icon: BrainCircuit, title: "Agents activate", body: "Orchestrator spins up CoderData, OperationsEngineering, and WebSearch agents in parallel." },
              { n: "03", icon: Settings2, title: "Reason & cross-reference", body: "Agents query live sensor telemetry, OEM manuals, and maintenance history simultaneously." },
              { n: "04", icon: Zap, title: "Human reviews", body: "Approval card sent to lead engineer — one click to approve before the report reaches the team." },
              { n: "05", icon: Mail, title: "Report delivered", body: "Structured health report sent to the full engineering team via Microsoft Graph." },
            ].map(({ n, icon: Icon, title, body }) => (
              <div key={n} className="landing-step">
                <div className="landing-step-num">{n}</div>
                <div className="landing-step-icon"><Icon className="h-5 w-5" /></div>
                <div className="landing-step-title">{title}</div>
                <div className="landing-step-body">{body}</div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── Capabilities ── */}
      <section className="landing-section landing-section-alt">
        <div className="landing-section-inner">
          <p className="landing-eyebrow">Capabilities</p>
          <h2 className="landing-section-title">Everything your team needs in one platform.</h2>

          <div className="landing-caps-grid">
            {[
              { icon: BrainCircuit, title: "Multi-Agent Orchestration", body: "Specialist agents run in parallel — sensor analysis, OEM knowledge base, and industry research — orchestrated into a single unified output." },
              { icon: Bot, title: "Knowledge-Grounded Analysis", body: "Cross-references live readings against your Emerson CSER2000 thresholds and Iqbal maintenance guidelines using Retrieval-Augmented Generation." },
              { icon: Mail, title: "Human-in-the-Loop Actions", body: "The agent proposes. You decide. Email confirmation gate ensures no report goes out without your explicit approval." },
              { icon: Calendar, title: "Autonomous Scheduling", body: "Configure weekly or daily reports conversationally. Tell the agent when and what — it sets up the schedule and confirms the details back to you." },
              { icon: Zap, title: "Agentic Actions", body: "From diagnosis to email delivery, the platform takes multi-step autonomous action — querying data, reading documents, and communicating results." },
              { icon: Settings2, title: "Enterprise Security", body: "Managed identity on Azure Container Apps. No passwords stored. Microsoft Graph API for mail. Azure AI Foundry for model governance." },
            ].map(({ icon: Icon, title, body }) => (
              <div key={title} className="landing-cap-card">
                <div className="landing-cap-icon"><Icon className="h-5 w-5" /></div>
                <div className="landing-cap-title">{title}</div>
                <div className="landing-cap-body">{body}</div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── CTA Banner ── */}
      <section className="landing-cta-banner">
        <div className="landing-section-inner landing-cta-inner">
          <h2 className="landing-cta-title">Ready to eliminate unplanned downtime?</h2>
          <p className="landing-cta-sub">
            Two assets. Real sensor data. OEM-grounded reasoning. Start now.
          </p>
          <Link href="/chat" className="landing-primary-btn landing-primary-btn-lg">
            Launch Platform <ChevronRight className="h-5 w-5" />
          </Link>
        </div>
      </section>

      {/* ── Footer ── */}
      <footer className="landing-footer">
        <div className="landing-nav-inner">
          <span className="landing-footer-copy">© 2026 Wragby Solutions · Multi-Agentic AI Framework</span>
          <span className="landing-footer-copy">Built on Microsoft Azure AI Foundry</span>
        </div>
      </footer>

    </div>
  );
}
