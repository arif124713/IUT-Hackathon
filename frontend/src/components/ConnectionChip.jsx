export default function ConnectionChip({ connected }) {
  return (
    <span className={`chip ${connected ? "chip-live" : "chip-reconnecting"}`}>
      <span className="chip-dot" />
      {connected ? "Live" : "Reconnecting…"}
    </span>
  );
}
