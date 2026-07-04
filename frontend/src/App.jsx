import { useMemo, useState, useEffect } from "react";
import useLiveOffice from "./hooks/useLiveOffice";
import ConnectionChip from "./components/ConnectionChip";
import PowerMeter from "./components/PowerMeter";
import RoomCard from "./components/RoomCard";
import AlertsPanel from "./components/AlertsPanel";
import OfficeMap from "./components/OfficeMap";
import PowerTrendChart from "./components/PowerTrendChart";

function DhakaClock() {
  const [time, setTime] = useState(() =>
    new Date().toLocaleTimeString("en-US", {
      timeZone: "Asia/Dhaka",
      hour: "2-digit",
      minute: "2-digit",
      second: "2-digit",
    })
  );

  useEffect(() => {
    const id = setInterval(() => {
      setTime(
        new Date().toLocaleTimeString("en-US", {
          timeZone: "Asia/Dhaka",
          hour: "2-digit",
          minute: "2-digit",
          second: "2-digit",
        })
      );
    }, 1000);
    return () => clearInterval(id);
  }, []);

  return <span className="clock">{time} BGT</span>;
}

const ROOMS = ["drawing", "work1", "work2"];

export default function App() {
  const { devices, power, alerts, connected } = useLiveOffice();

  const byRoom = useMemo(() => {
    const map = {};
    ROOMS.forEach((r) => (map[r] = []));
    devices.forEach((d) => {
      if (map[d.room]) map[d.room].push(d);
    });
    return map;
  }, [devices]);

  return (
    <div className="app">
      <header className="header">
        <h1>⚡ OfficePulse</h1>
        <DhakaClock />
        <ConnectionChip connected={connected} />
      </header>

      <div className="top-row">
        <PowerMeter power={power} />
        <OfficeMap devices={devices} />
      </div>

      <PowerTrendChart totalW={power?.total_w} />

      <section className="device-section">
        {ROOMS.map((r) => (
          <RoomCard key={r} room={r} devices={byRoom[r] ?? []} />
        ))}
      </section>

      <AlertsPanel alerts={alerts} />
    </div>
  );
}
