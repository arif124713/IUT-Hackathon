import { useState, useEffect } from "react";

function fmt(dt) {
  if (!dt) return "—";
  return new Date(dt).toLocaleTimeString("en-US", { hour: "2-digit", minute: "2-digit" });
}

function FanIcon({ on }) {
  return (
    <svg width="36" height="36" viewBox="0 0 36 36" className={`device-svg-icon ${on ? "fan-icon-on" : ""}`}>
      {/* outer ring glow when on */}
      {on && <circle cx="18" cy="18" r="17" fill="none" stroke="#00bcd4" strokeWidth="1" opacity="0.4" className="fan-ring-pulse" />}
      {/* hub */}
      <circle cx="18" cy="18" r="4" fill={on ? "#00bcd4" : "#555"} />
      {/* 3 blades */}
      <g className={on ? "fan-blades-spin" : ""} style={{ transformOrigin: "18px 18px" }}>
        <path d="M18 14 C16 8, 10 7, 9 10 C8 13, 14 16, 18 14Z" fill={on ? "#00e5ff" : "#444"} opacity={on ? 0.9 : 0.5} />
        <path d="M18 14 C16 8, 10 7, 9 10 C8 13, 14 16, 18 14Z" fill={on ? "#00e5ff" : "#444"} opacity={on ? 0.9 : 0.5}
          transform="rotate(120 18 18)" />
        <path d="M18 14 C16 8, 10 7, 9 10 C8 13, 14 16, 18 14Z" fill={on ? "#00e5ff" : "#444"} opacity={on ? 0.9 : 0.5}
          transform="rotate(240 18 18)" />
      </g>
    </svg>
  );
}

function LightIcon({ on }) {
  return (
    <svg width="36" height="36" viewBox="0 0 36 36" className="device-svg-icon">
      {/* glow rings */}
      {on && <>
        <circle cx="18" cy="17" r="16" fill="rgba(255,183,0,0.08)" className="light-ring-3" />
        <circle cx="18" cy="17" r="12" fill="rgba(255,183,0,0.13)" className="light-ring-2" />
        <circle cx="18" cy="17" r="8"  fill="rgba(255,183,0,0.22)" className="light-ring-1" />
      </>}
      {/* rays */}
      {on && [0,45,90,135,180,225,270,315].map(deg => (
        <line key={deg}
          x1="18" y1="5" x2="18" y2="2"
          stroke="#ffca28" strokeWidth="1.5" strokeLinecap="round"
          transform={`rotate(${deg} 18 17)`}
          className="light-ray"
        />
      ))}
      {/* bulb body */}
      <path
        d="M14 19 C14 15.5, 16 13, 18 13 C20 13, 22 15.5, 22 19 L21 22 L15 22 Z"
        fill={on ? "#ffd54f" : "#2a2a3a"}
        stroke={on ? "#ffb300" : "#555"}
        strokeWidth="1"
      />
      {/* base */}
      <rect x="15" y="22" width="6" height="2" rx="1" fill={on ? "#ffb300" : "#444"} />
      <rect x="15.5" y="24" width="5" height="1.5" rx="0.75" fill={on ? "#ff8f00" : "#333"} />
    </svg>
  );
}

export default function DeviceTile({ device }) {
  const [flipped, setFlipped] = useState(false);

  useEffect(() => {
    setFlipped(true);
    const t = setTimeout(() => setFlipped(false), 400);
    return () => clearTimeout(t);
  }, [device.status]);

  const isFan = device.type === "fan";
  const on = device.status;

  return (
    <div className={[
      "device-tile",
      on ? "tile-on" : "tile-off",
      isFan ? "tile-fan" : "tile-light",
      flipped ? "tile-flip" : "",
    ].filter(Boolean).join(" ")}>

      {/* colored left bar */}
      <div className="tile-bar" />

      <div className="tile-icon-wrap">
        {isFan ? <FanIcon on={on} /> : <LightIcon on={on} />}
      </div>

      <div className="tile-info">
        <span className="device-name">{device.name}</span>
        <span className="device-last">Changed {fmt(device.last_changed)}</span>
      </div>

      <div className="tile-right">
        <span className={`pill ${on ? "pill-on" : "pill-off"}`}>{on ? "ON" : "OFF"}</span>
        <span className="device-watt">{device.wattage}W</span>
      </div>
    </div>
  );
}
