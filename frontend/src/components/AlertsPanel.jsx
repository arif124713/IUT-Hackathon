function fmt(dt) {
  if (!dt) return "";
  return new Date(dt).toLocaleTimeString("en-US", { hour: "2-digit", minute: "2-digit" });
}

const TYPE_COLOR = {
  after_hours:  "alert-amber",
  marathon_room: "alert-red",
  high_load:    "alert-red",
};

export default function AlertsPanel({ alerts }) {
  const active = alerts.filter((a) => a.active);
  const resolved = alerts.filter((a) => !a.active).slice(0, 3);

  if (active.length === 0 && resolved.length === 0) {
    return (
      <div className="alerts-panel empty">
        <span>✅ All quiet — nothing burning money right now.</span>
      </div>
    );
  }

  return (
    <div className="alerts-panel">
      <h3>Alerts</h3>
      {active.map((a) => (
        <div key={a.id} className={`alert-item ${TYPE_COLOR[a.type] ?? "alert-amber"}`}>
          <span className="alert-dot">⚠</span>
          <div className="alert-body">
            <span className="alert-msg">{a.message}</span>
            <span className="alert-time">{fmt(a.triggered_at)}</span>
          </div>
        </div>
      ))}
      {resolved.length > 0 && (
        <details className="resolved-details">
          <summary>Resolved ({resolved.length})</summary>
          {resolved.map((a) => (
            <div key={a.id} className="alert-item alert-resolved">
              <span className="alert-dot">✓</span>
              <span className="alert-msg">{a.message}</span>
              <span className="alert-time">{fmt(a.resolved_at)}</span>
            </div>
          ))}
        </details>
      )}
    </div>
  );
}
