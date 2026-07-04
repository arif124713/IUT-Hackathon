const ROOMS_LAYOUT = [
  { id: "drawing", label: "Drawing Room", x: 20,  y: 20, w: 200, h: 170 },
  { id: "work1",   label: "Work Room 1",  x: 250, y: 20, w: 200, h: 170 },
  { id: "work2",   label: "Work Room 2",  x: 480, y: 20, w: 200, h: 170 },
];

const DEVICE_POSITIONS = {
  drawing: [
    { id: "drawing-fan-1",   rx: 55,  ry: 65 },
    { id: "drawing-fan-2",   rx: 145, ry: 65 },
    { id: "drawing-light-1", rx: 40,  ry: 135 },
    { id: "drawing-light-2", rx: 100, ry: 135 },
    { id: "drawing-light-3", rx: 160, ry: 135 },
  ],
  work1: [
    { id: "work1-fan-1",   rx: 55,  ry: 65 },
    { id: "work1-fan-2",   rx: 145, ry: 65 },
    { id: "work1-light-1", rx: 40,  ry: 135 },
    { id: "work1-light-2", rx: 100, ry: 135 },
    { id: "work1-light-3", rx: 160, ry: 135 },
  ],
  work2: [
    { id: "work2-fan-1",   rx: 55,  ry: 65 },
    { id: "work2-fan-2",   rx: 145, ry: 65 },
    { id: "work2-light-1", rx: 40,  ry: 135 },
    { id: "work2-light-2", rx: 100, ry: 135 },
    { id: "work2-light-3", rx: 160, ry: 135 },
  ],
};

function FanGlyph({ x, y, on }) {
  // Same teardrop blade as DeviceTile fan, but translated from (18,18) origin to (0,0)
  // Original: M18 14 C16 8, 10 7, 9 10 C8 13, 14 16, 18 14Z  →  subtract (18,18)
  const blade = "M0,-4 C-2,-10,-8,-11,-9,-8 C-10,-5,-4,-2,0,-4 Z";

  return (
    <g transform={`translate(${x},${y})`}>
      {on && <circle r="22" fill="none" stroke="#00bcd4" strokeWidth="1.5" opacity="0.35" className="map-fan-ring" />}
      <circle r="16" fill={on ? "#0a2535" : "#1a1a2e"} stroke={on ? "#00bcd4" : "#2a2a44"} strokeWidth={on ? 1.5 : 1} />

      {/* blades — transform-box:fill-box + transform-origin:center = rotate around own center */}
      <g className={on ? "map-fan-spin" : ""}>
        <path d={blade} fill={on ? "#00e5ff" : "#3a3a4a"} opacity={on ? 0.95 : 0.55} />
        <path d={blade} fill={on ? "#00e5ff" : "#3a3a4a"} opacity={on ? 0.95 : 0.55} transform="rotate(120)" />
        <path d={blade} fill={on ? "#00e5ff" : "#3a3a4a"} opacity={on ? 0.95 : 0.55} transform="rotate(240)" />
      </g>

      {/* hub */}
      <circle r="3.5" fill={on ? "#00bcd4" : "#555"} />
      <circle r="1.5" fill={on ? "#e0f7fa" : "#222"} />

      <text y="28" textAnchor="middle" fontSize="9" fill={on ? "#00bcd4" : "#555"}>
        {on ? "ON" : "OFF"}
      </text>
    </g>
  );
}

function LightGlyph({ x, y, on }) {
  return (
    <g transform={`translate(${x},${y})`}>
      {/* multi-layer glow halos */}
      {on && <>
        <circle r="30" fill="rgba(255,180,0,0.05)" className="map-light-halo-3" />
        <circle r="22" fill="rgba(255,180,0,0.10)" className="map-light-halo-2" />
        <circle r="14" fill="rgba(255,180,0,0.20)" className="map-light-halo-1" />
      </>}
      {/* rays */}
      {on && [0,45,90,135,180,225,270,315].map(deg => (
        <line key={deg}
          x1="0" y1="-10" x2="0" y2="-16"
          stroke="#ffca28" strokeWidth="1.5" strokeLinecap="round"
          transform={`rotate(${deg})`}
          className="map-light-ray"
        />
      ))}
      {/* bulb */}
      <circle r="8" fill={on ? "#ffd54f" : "#2a2a3a"} stroke={on ? "#ffb300" : "#444"} strokeWidth={on ? 1.5 : 1} />
      <circle r="4" fill={on ? "#fff9c4" : "#1e1e2e"} />
      {/* label */}
      <text y="20" textAnchor="middle" fontSize="9" fill={on ? "#ffb300" : "#555"}>
        {on ? "ON" : "OFF"}
      </text>
    </g>
  );
}

function RoomAmbient({ room, devicesOn, total }) {
  // ambient tint behind the room when devices are on
  const ratio = total > 0 ? devicesOn / total : 0;
  if (ratio === 0) return null;
  return (
    <rect
      x={room.x + 1} y={room.y + 1}
      width={room.w - 2} height={room.h - 2}
      rx="7"
      fill={`rgba(0,188,212,${(ratio * 0.06).toFixed(3)})`}
      className="room-ambient"
    />
  );
}

export default function OfficeMap({ devices }) {
  const deviceMap = Object.fromEntries((devices ?? []).map(d => [d.id, d]));

  return (
    <div className="office-map">
      <h4>Office Layout</h4>
      <svg viewBox="0 0 700 210" width="100%" style={{ maxWidth: 700 }}>
        <defs>
          <filter id="glow-amber">
            <feGaussianBlur stdDeviation="3" result="blur" />
            <feMerge><feMergeNode in="blur"/><feMergeNode in="SourceGraphic"/></feMerge>
          </filter>
          <filter id="glow-cyan">
            <feGaussianBlur stdDeviation="3" result="blur" />
            <feMerge><feMergeNode in="blur"/><feMergeNode in="SourceGraphic"/></feMerge>
          </filter>
        </defs>

        {ROOMS_LAYOUT.map(room => {
          const roomDevices = DEVICE_POSITIONS[room.id] ?? [];
          const onCount = roomDevices.filter(p => deviceMap[p.id]?.status).length;

          return (
            <g key={room.id}>
              {/* room border */}
              <rect x={room.x} y={room.y} width={room.w} height={room.h}
                rx="8" fill="#16162a" stroke="#2a2a44" strokeWidth="1.5" />
              {/* ambient room glow */}
              <RoomAmbient room={room} devicesOn={onCount} total={roomDevices.length} />
              {/* room label */}
              <text x={room.x + room.w / 2} y={room.y + 15}
                textAnchor="middle" fontSize="10" fill="#666" fontWeight="500">
                {room.label}
              </text>
              {/* divider line between fans and lights */}
              <line x1={room.x + 10} y1={room.y + 95} x2={room.x + room.w - 10} y2={room.y + 95}
                stroke="#2a2a44" strokeWidth="1" strokeDasharray="3 3" />

              {/* devices */}
              {roomDevices.map(pos => {
                const dev = deviceMap[pos.id];
                const isOn = dev?.status ?? false;
                const isFan = pos.id.includes("fan");
                const ax = room.x + pos.rx;
                const ay = room.y + pos.ry;
                return isFan
                  ? <FanGlyph key={pos.id} x={ax} y={ay} on={isOn} />
                  : <LightGlyph key={pos.id} x={ax} y={ay} on={isOn} />;
              })}
            </g>
          );
        })}
      </svg>
    </div>
  );
}
