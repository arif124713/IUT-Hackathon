const MAX_W = 570; // 3 rooms × 190 W
const ROOM_LABELS = { drawing: "Drawing", work1: "Work 1", work2: "Work 2" };

export default function PowerMeter({ power }) {
  if (!power) return <div className="power-meter skeleton" />;

  const pct = Math.min((power.total_w / MAX_W) * 100, 100);

  return (
    <div className="power-meter">
      <div className="meter-dial">
        <svg viewBox="0 0 120 70" width="180">
          <path d="M10,65 A55,55 0 0,1 110,65" fill="none" stroke="#2a2a3a" strokeWidth="12" />
          <path
            d="M10,65 A55,55 0 0,1 110,65"
            fill="none"
            stroke={pct > 80 ? "#ef5350" : pct > 50 ? "#ffb300" : "#00bcd4"}
            strokeWidth="12"
            strokeDasharray={`${(pct / 100) * 173} 173`}
          />
          <text x="60" y="62" textAnchor="middle" fontSize="18" fontWeight="bold" fill="#e0e0e0">
            {Math.round(power.total_w)}W
          </text>
        </svg>
      </div>

      <div className="meter-details">
        {Object.entries(power.by_room).map(([room, w]) => (
          <div key={room} className="room-bar">
            <span className="rb-label">{ROOM_LABELS[room] ?? room}</span>
            <div className="rb-track">
              <div className="rb-fill" style={{ width: `${Math.min((w / 190) * 100, 100)}%` }} />
            </div>
            <span className="rb-val">{Math.round(w)}W</span>
          </div>
        ))}
        <div className="kwh-row">
          <span>Today</span>
          <strong>{power.today_kwh} kWh</strong>
        </div>
      </div>
    </div>
  );
}
