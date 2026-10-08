"use client";

import { useEffect, useRef, useState } from "react";
import { WS_URL } from "@/lib/api";
import type { Telemetry } from "@/types/telemetry";

export interface HistoryPoint {
  ear: number;
  mar: number;
}

const HISTORY = 60;

export function useTelemetry() {
  const [telemetry, setTelemetry] = useState<Telemetry | null>(null);
  const [connected, setConnected] = useState(false);
  const [history, setHistory] = useState<HistoryPoint[]>([]);
  const retry = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    let ws: WebSocket | null = null;
    let closed = false;

    const connect = () => {
      ws = new WebSocket(WS_URL);
      ws.onopen = () => setConnected(true);
      ws.onmessage = (msg) => {
        try {
          const t = JSON.parse(msg.data) as Telemetry;
          setTelemetry(t);
          setHistory((h) => [...h.slice(-(HISTORY - 1)), { ear: t.ear, mar: t.mar }]);
        } catch {
          /* bỏ qua bản tin lỗi */
        }
      };
      ws.onclose = () => {
        setConnected(false);
        if (!closed) retry.current = setTimeout(connect, 1500);
      };
      ws.onerror = () => ws?.close();
    };
    connect();

    return () => {
      closed = true;
      if (retry.current) clearTimeout(retry.current);
      ws?.close();
    };
  }, []);

  return { telemetry, connected, history };
}
