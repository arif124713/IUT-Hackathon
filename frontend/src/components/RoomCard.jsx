import DeviceTile from "./DeviceTile";

const ROOM_LABELS = { drawing: "Drawing Room", work1: "Work Room 1", work2: "Work Room 2" };

export default function RoomCard({ room, devices }) {
  const on = devices.filter((d) => d.status).length;
  const totalW = devices.filter((d) => d.status).reduce((s, d) => s + d.wattage, 0);

  return (
    <div className="room-card">
      <div className="room-header">
        <h3>{ROOM_LABELS[room] ?? room}</h3>
        <span className="room-stats">
          {on}/{devices.length} on · {totalW}W
        </span>
      </div>
      <div className="device-grid">
        {devices.map((d) => (
          <DeviceTile key={d.id} device={d} />
        ))}
      </div>
    </div>
  );
}
