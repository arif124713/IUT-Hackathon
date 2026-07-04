import { useEffect, useReducer, useRef, useState } from "react";

const WS_URL = `${window.location.protocol === "https:" ? "wss:" : "ws:"}//${window.location.host}/ws/live`;

function reducer(state, action) {
  switch (action.type) {
    case "SNAPSHOT":
      return { ...action.payload };

    case "DEVICE_UPDATE": {
      const { id, status, last_changed } = action.data;
      const devices = state.devices.map((d) =>
        d.id === id
          ? { ...d, status, current_draw_w: status ? d.wattage : 0, last_changed }
          : d
      );
      return { ...state, devices };
    }

    case "POWER_UPDATE":
      return {
        ...state,
        power: {
          ...state.power,
          total_w: action.data.total_w,
          by_room: action.data.by_room,
        },
      };

    case "ALERT": {
      const incoming = action.data;
      const alerts = state.alerts.filter((a) => a.id !== incoming.id);
      if (incoming.active !== false) alerts.unshift(incoming);
      return { ...state, alerts };
    }

    default:
      return state;
  }
}

const INITIAL = { devices: [], power: null, alerts: [] };

export default function useLiveOffice() {
  const [state, dispatch] = useReducer(reducer, INITIAL);
  const [connected, setConnected] = useState(false);
  const wsRef = useRef(null);

  useEffect(() => {
    let backoff = 500;

    async function fetchSnapshot() {
      const r = await fetch("/api/summary");
      const data = await r.json();
      dispatch({ type: "SNAPSHOT", payload: { devices: data.devices, power: data.power, alerts: data.alerts } });
    }

    function connect() {
      const ws = new WebSocket(WS_URL);
      wsRef.current = ws;

      ws.onopen = () => {
        setConnected(true);
        backoff = 500;
        fetchSnapshot();
      };

      ws.onmessage = (e) => {
        const msg = JSON.parse(e.data);
        if (msg.event === "device_update") dispatch({ type: "DEVICE_UPDATE", data: msg.data });
        else if (msg.event === "power_update") dispatch({ type: "POWER_UPDATE", data: msg.data });
        else if (msg.event === "alert") dispatch({ type: "ALERT", data: msg.data });
      };

      ws.onclose = () => {
        setConnected(false);
        setTimeout(connect, backoff);
        backoff = Math.min(backoff * 2, 16000);
      };

      ws.onerror = () => ws.close();
    }

    connect();
    return () => wsRef.current?.close();
  }, []);

  return { ...state, connected };
}
