"use client";

import { useEffect, useState } from "react";
import type { Telemetry } from "@/types/telemetry";
import { getHealth, type Health } from "@/lib/health";
import { LevelMark } from "./monitor-ui";

function Metric({ label, value, unit }: { label: string; value?: number; unit: string }) {
  return <div className="monitor-metric"><dt className="monitor-muted">{label}</dt><dd className="mt-1 font-semibold tabular-nums">{value === undefined ? "Chưa có dữ liệu" : `${value.toFixed(1)} ${unit}`}</dd></div>;
}

export function SystemHealth({ telemetry, connected }: { telemetry: Telemetry | null; connected: boolean }) {
  const [health, setHealth] = useState<Health | null>(null);
  const [error, setError] = useState(false);
  useEffect(() => {
    let alive = true;
    const load = async () => {
      try { const result = await getHealth(); if (alive) { setHealth(result); setError(false); } }
      catch { if (alive) setError(true); }
    };
    void load();
    const timer = setInterval(() => void load(), 5000);
    return () => { alive = false; clearInterval(timer); };
  }, []);
  return <section className="monitor-panel">
    <h2 className="monitor-panel-title">Sức khỏe hệ thống</h2>
    <div className="mb-4 grid gap-2 sm:grid-cols-2 lg:grid-cols-4 text-sm">
      <div>WebSocket: <LevelMark level={connected ? "NORMAL" : "DANGER"}/>{!connected && <p className="monitor-muted">Đang thử kết nối lại.</p>}</div>
      <div>API: {error ? <><LevelMark level="DANGER"/><p className="monitor-muted">Không tải được. Kiểm tra API.</p></> : health ? <><LevelMark level={health.status === "ok" ? "NORMAL" : "WARNING"}/><span className="ml-1">({health.status})</span></> : "Đang kiểm tra…"}</div>
      <div>AI worker: {health ? <LevelMark level={health.ai_worker_alive ? "NORMAL" : "WARNING"}/> : "Đang kiểm tra…"}</div>
      <div>Camera: {health ? <LevelMark level={health.camera_connected ? "NORMAL" : "WARNING"}/> : "Đang kiểm tra…"}</div>
    </div>
    <dl className="grid gap-2 sm:grid-cols-2 lg:grid-cols-5"><Metric label="FPS camera" value={telemetry?.fps.camera} unit="fps"/><Metric label="FPS mặt" value={telemetry?.fps.face} unit="fps"/><Metric label="FPS điện thoại" value={telemetry?.fps.phone} unit="fps"/><Metric label="Độ trễ mặt" value={telemetry?.latency_ms.face} unit="ms"/><Metric label="Độ trễ điện thoại" value={telemetry?.latency_ms.phone} unit="ms"/></dl>
  </section>;
}
