===ACP_EOF===
===ACP_FILE: dashboard-frontend/src/App.jsx===
import { useState, useMemo } from "react";

const SEVERITY_ORDER = { critical: 0, high: 1, medium: 2, low: 3, info: 4 };
const SEVERITY_COLORS = {
  critical: { bg: "#7f1d1d", badge: "#dc2626", text: "#fca5a5" },
  high:     { bg: "#7c2d12", badge: "#ea580c", text: "#fdba74" },
  medium:   { bg: "#713f12", badge: "#ca8a04", text: "#fde047" },
  low:      { bg: "#14532d", badge: "#16a34a", text: "#86efac" },
  info:     { bg: "#1e3a5f", badge: "#3b82f6", text: "#93c5fd" },
};
const STATUS_LABELS = { new: "New", triaging: "Triaging", acknowledged: "Acknowledged", resolved: "Resolved", suppressed: "Suppressed" };

const MOCK_INCIDENTS = [
  { id: "INC-001", title: "Database cluster failover detected", severity: "critical", status: "new", service: "db-primary", count: 12, created: "2025-01-15T08:23:00Z", assignee: null, description: "Primary database node db-01 has failed over to db-02. Multiple connection errors reported by application services." },
  { id: "INC-002", title: "API latency spike on /api/v2/users", severity: "high", status: "triaging", service: "api-gateway", count: 8, created: "2025-01-15T08:20:00Z", assignee: "alice", description: "P99 latency for /api/v2/users endpoint exceeded 5s threshold. Correlated with increased error rates." },
  { id: "INC-003", title: "Disk usage above 85% on worker-03", severity: "medium", status: "acknowledged", service: "worker-pool", count: 3, created: "2025-01-15T07:45:00Z", assignee: "bob", description: "Worker node worker-03 disk utilization at 87%. Log rotation may be stalled." },
  { id: "INC-004", title: "SSL certificate expiring in 7 days", severity: "low", status: "new", service: "lb-prod", count: 1, created: "2025-01-15T06:00:00Z", assignee: null, description: "TLS certificate for *.example.com expires on 2025-01-22. Auto-renewal may need verification." },
  { id: "INC-005", title: "Stale Prometheus scrape target", severity: "info", status: "suppressed", service: "monitoring", count: 1, created: "2025-01-14T22:10:00Z", assignee: "carol", description: "Prometheus target node-exporter-14 has been stale for 6h. Node decommissioned; target removal pending." },
  { id: "INC-006", title: "Kubernetes pod crash-loop in payments", severity: "critical", status: "new", service: "payments-svc", count: 24, created: "2025-01-15T08:25:00Z", assignee: null, description: "Payment service pods entering CrashLoopBackOff. OOMKilled events observed. Investigating memory limit configuration." },
  { id: "INC-007", title: "Redis sentinel split-brain warning", severity: "high", status: "triaging", service: "redis-cluster", count: 5, created: "2025-01-15T08:10:00Z", assignee: "dave", description: "Redis sentinels disagree on master node. Potential data inconsistency if writes continue on both nodes." },
  { id: "INC-008", title: "Deployment rollback triggered for auth-svc", severity: "medium", status: "acknowledged", service: "auth-svc", count: 2, created: "2025-01-15T07:30:00Z", assignee: "eve", description: "Automated rollback of auth-svc v2.3.1 due to health check failures. Previous version v2.3.0 restored." },
];

function Badge({ children, color }) {
  return (
    <span style={{ backgroundColor: color, color: "#fff", padding: "2px 8px", borderRadius: "9999px", fontSize: "0.75rem", fontWeight: 600, whiteSpace: "nowrap" }}>
      {children}
    </span>
  );
}

function IncidentRow({ incident, isSelected, onSelect }) {
  const c = SEVERITY_COLORS[incident.severity];
  return (
    <tr
      onClick={() => onSelect(incident)}
      style={{
        cursor: "pointer",
        backgroundColor: isSelected ? "#1e293b" : (incident.severity === "critical" && incident.status === "new" ? c.bg : "transparent"),
        borderBottom: "1px solid #1e293b",
        transition: "background-color 0.15s",
      }}
    >
      <td style={{ padding: "10px 12px", fontFamily: "monospace", color: "#94a3b8" }}>{incident.id}</td>
      <td style={{ padding: "10px 12px", color: "#e2e8f0", fontWeight: 500 }}>{incident.title}</td>
      <td style={{ padding: "10px 12px" }}><Badge color={c.badge}>{incident.severity.toUpperCase()}</Badge></td>
      <td style={{ padding: "10px 12px", color: "#cbd5e1" }}>{STATUS_LABELS[incident.status]}</td>
      <td style={{ padding: "10px 12px", color: "#94a3b8" }}>{incident.service}</td>
      <td style={{ padding: "10px 12px", color: "#94a3b8", textAlign: "center" }}>{incident.count}</td>
      <td style={{ padding: "10px 12px", color: "#64748b" }}>{new Date(incident.created).toLocaleTimeString()}</td>
    </tr>
  );
}

function DetailPanel({ incident, onClose, onStatusChange }) {
  if (!incident) return null;
  const c = SEVERITY_COLORS[incident.severity];
  return (
    <div style={{ position: "fixed", right: 0, top: 0, bottom: 0, width: "420px", backgroundColor: "#0f172a", borderLeft: "1px solid #1e293b", padding: "24px", overflowY: "auto", zIndex: 50, boxShadow: "-4px 0 24px rgba(0,0,0,0.5)" }}>
      <button onClick={onClose} style={{ position: "absolute", top: "12px", right: "12px", background: "none", border: "none", color: "#64748b", fontSize: "1.25rem", cursor: "pointer" }}>✕</button>
      <div style={{ marginBottom: "16px" }}>
        <span style={{ color: "#64748b", fontSize: "0.8rem", fontFamily: "monospace" }}>{incident.id}</span>
        <h2 style={{ color: "#f1f5f9", margin: "8px 0 12px", fontSize: "1.1rem" }}>{incident.title}</h2>
        <div style={{ display: "flex", gap: "8px", alignItems: "center" }}>
          <Badge color={c.badge}>{incident.severity.toUpperCase()}</Badge>
          <Badge color="#475569">{STATUS_LABELS[incident.status]}</Badge>
        </div>
      </div>
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "12px", marginBottom: "20px" }}>
        <div><span style={{ color: "#64748b", fontSize: "0.75rem" }}>Service</span><div style={{ color: "#cbd5e1" }}>{incident.service}</div></div>
        <div><span style={{ color: "#64748b", fontSize: "0.75rem" }}>Alert Count</span><div style={{ color: "#cbd5e1" }}>{incident.count}</div></div>
        <div><span style={{ color: "#64748b", fontSize: "0.75rem" }}>Assignee</span><div style={{ color: "#cbd5e1" }}>{incident.assignee || "Unassigned"}</div></div>
        <div><span style={{ color: "#64748b", fontSize: "0.75rem" }}>Created</span><div style={{ color: "#cbd5e1" }}>{new Date(incident.created).toLocaleString()}</div></div>
      </div>
      <div style={{ marginBottom: "24px" }}>
        <span style={{ color: "#64748b", fontSize: "0.75rem" }}>Description</span>
        <p style={{ color: "#94a3b8", fontSize: "0.9rem", lineHeight: 1.6, marginTop: "4px" }}>{incident.description}</p>
      </div>
      <div>
        <span style={{ color: "#64748b", fontSize: "0.75rem", display: "block", marginBottom: "8px" }}>Update Status</span>
        <div style={{ display: "flex", gap: "6px", flexWrap: "wrap" }}>
          {Object.entries(STATUS_LABELS).map(([key, label]) => (
            <button key={key} onClick={() => onStatusChange(incident.id, key)} disabled={incident.status === key}
              style={{
                padding: "6px 12px", borderRadius: "6px", border: "1px solid #334155", backgroundColor: incident.status === key ? SEVERITY_COLORS[incident.severity].badge : "#1e293b",
                color: incident.status === key ? "#fff" : "#94a3b8", cursor: incident.status === key ? "default" : "pointer", fontSize: "0.8rem", fontWeight: 500,
              }}>
              {label}
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}

export default function App() {
  const [incidents, setIncidents] = useState(MOCK_INCIDENTS);
  const [selectedId, setSelectedId] = useState(null);
  const [severityFilter, setSeverityFilter] = useState("all");
  const [statusFilter, setStatusFilter] = useState("all");

  const filtered = useMemo(() => {
    return incidents
      .filter((inc) => severityFilter === "all" || inc.severity === severityFilter)
      .filter((inc) => statusFilter === "all" || inc.status === statusFilter)
      .sort((a, b) => SEVERITY_ORDER[a.severity] - SEVERITY_ORDER[b.severity] || new Date(b.created) - new Date(a.created));
  }, [incidents, severityFilter, statusFilter]);

  const selected = incidents.find((i) => i.id === selectedId) || null;

  const handleStatusChange = (id, newStatus) => {
    setIncidents((prev) => prev.map((inc) => (inc.id === id ? { ...inc, status: newStatus } : inc)));
    setSelectedId(id);
  };

  const counts = useMemo(() => {
    const c = { all: incidents.length };
    for (const inc of incidents) {
      c[inc.severity] = (c[inc.severity] || 0) + 1;
    }
    return c;
  }, [incidents]);

  return (
    <div style={{ fontFamily: "'Inter', system-ui, sans-serif", backgroundColor: "#020617", color: "#e2e8f0", minHeight: "100vh", display: "flex", flexDirection: "column" }}>
      <header style={{ padding: "20px 24px", borderBottom: "1px solid #1e293b" }}>
        <h1 style={{ fontSize: "1.25rem", fontWeight: 700, margin: 0, letterSpacing: "-0.025em" }}>Incident Triage Dashboard</h1>
        <p style={{ color: "#475569", fontSize: "0.8rem", margin: "4px 0 0" }}>{incidents.length} incidents · {incidents.filter((i) => i.status === "new").length} new</p>
      </header>

      <div style={{ padding: "16px 24px", display: "flex", gap: "12px", borderBottom: "1px solid #1e293b", flexWrap: "wrap", alignItems: "center" }}>
        <span style={{ color: "#64748b", fontSize: "0.8rem", fontWeight: 600 }}>SEVERITY</span>
        {["all", ...Object.keys(SEVERITY_ORDER)].map((sev) => (
          <button key={sev} onClick={() => setSeverityFilter(sev)}
            style={{
              padding: "4px 12px", borderRadius: "6px", border: "1px solid", fontSize: "0.8rem", fontWeight: 500, cursor: "pointer",
              borderColor: severityFilter === sev ? (SEVERITY_COLORS[sev]?.badge || "#3b82f6") : "#1e293b",
              backgroundColor: severityFilter === sev ? (SEVERITY_COLORS[sev]?.badge || "#3b82f6") : "transparent",
              color: severityFilter === sev ? "#fff" : "#94a3b8",
            }}>
            {sev === "all" ? "All" : sev.charAt(0).toUpperCase() + sev.slice(1)} ({counts[sev] || 0})
          </button>
        ))}
        <span style={{ color: "#334155", margin: "0 4px" }}>|</span>
        <span style={{ color: "#64748b", fontSize: "0.8rem", fontWeight: 600 }}>STATUS</span>
        {["all", ...Object.keys(STATUS_LABELS)].map((st) => (
          <button key={st} onClick={() => setStatusFilter(st)}
            style={{
              padding: "4px 12px", borderRadius: "6px", border: "1px solid", fontSize: "0.8rem", fontWeight: 500, cursor: "pointer",
              borderColor: statusFilter === st ? "#3b82f6" : "#1e293b",
              backgroundColor: statusFilter === st ? "#1e3a5f" : "transparent",
              color: statusFilter === st ? "#93c5fd" : "#94a3b8",
            }}>
            {st === "all" ? "All" : STATUS_LABELS[st]}
          </button>
        ))}
      </div>

      <main style={{ flex: 1, overflow: "auto" }}>
        <table style={{ width: "100%", borderCollapse: "collapse" }}>
          <thead>
            <tr style={{ borderBottom: "2px solid #1e293b" }}>
              {["ID", "Title", "Severity", "Status", "Service", "Alerts", "Time"].map((h) => (
                <th key={h} style={{ padding: "10px 12px", textAlign: h === "Alerts" ? "center" : "left", color: "#475569", fontSize: "0.75rem", fontWeight: 600, letterSpacing: "0.05em" }}>{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {filtered.map((inc) => (
              <IncidentRow key={inc.id} incident={inc} isSelected={selectedId === inc.id} onSelect={(i) => setSelectedId(selectedId === i.id ? null : i.id)} />
            ))}
            {filtered.length === 0 && (
              <tr><td colSpan={7} style={{ padding: "40px", textAlign: "center", color: "#475569" }}>No incidents match the current filters.</td></tr>
            )}
          </tbody>
        </table>
      </main>

      {selectedId && <DetailPanel incident={selected} onClose={() => setSelectedId(null)} onStatusChange={handleStatusChange} />}
    </div>
  );
}