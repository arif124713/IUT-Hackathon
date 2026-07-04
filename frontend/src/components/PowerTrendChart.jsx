import { useEffect, useRef, useState } from "react";
import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer } from "recharts";

const MAX_POINTS = 36; // 30 min at 5-second ticks = 360 points — keep last 36 for readability

export default function PowerTrendChart({ totalW }) {
  const [history, setHistory] = useState([]);
  const tick = useRef(0);

  useEffect(() => {
    if (totalW == null) return;
    tick.current += 1;
    const label = `${tick.current * 5}s`;
    setHistory((h) => {
      const next = [...h, { t: label, w: Math.round(totalW) }];
      return next.slice(-MAX_POINTS);
    });
  }, [totalW]);

  if (history.length < 2) return null;

  return (
    <div className="trend-chart">
      <h4>Power Trend (last ~3 min)</h4>
      <ResponsiveContainer width="100%" height={120}>
        <LineChart data={history}>
          <XAxis dataKey="t" tick={false} />
          <YAxis domain={[0, 600]} tick={{ fontSize: 11, fill: "#888" }} width={40} />
          <Tooltip
            contentStyle={{ background: "#1e1e2e", border: "1px solid #333", borderRadius: 6 }}
            labelStyle={{ color: "#aaa" }}
            itemStyle={{ color: "#00bcd4" }}
          />
          <Line type="monotone" dataKey="w" stroke="#00bcd4" dot={false} strokeWidth={2} />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
