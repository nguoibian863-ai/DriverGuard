"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { EarMarChart } from "@/components/charts/ear-mar-chart";
import { Controls } from "@/components/controls/controls";
import { DriverStatus } from "@/components/driver-status/driver-status";
import { RiskMeter } from "@/components/risk-meter/risk-meter";
import { VideoFeed } from "@/components/video-feed/video-feed";
import { EventTable } from "@/components/monitor/event-table";
import { RiskTimeline } from "@/components/monitor/risk-timeline";
import { SystemHealth } from "@/components/monitor/system-health";
import { useTelemetry } from "@/lib/useTelemetry";
import { useRiskHistory } from "@/lib/useRiskHistory";
import "./monitor.css";

export default function MonitorPage() {
  const { telemetry, connected, history } = useTelemetry();
  const { points, events } = useRiskHistory(telemetry);
  const [now, setNow] = useState(0);
  useEffect(() => { const update = () => setNow(Date.now()); update(); const timer = setInterval(update, 1000); return () => clearInterval(timer); }, []);
  return <main className="monitor-page"><div className="monitor-content">
    <header className="flex flex-wrap items-center justify-between gap-4"><h1 className="monitor-title">DriverGuard · Giám sát</h1><div className="flex flex-wrap items-center gap-4"><span className="monitor-connection"><span className={`monitor-connection-square ${connected ? "is-connected" : ""}`} aria-hidden="true"/>{connected ? "Đã kết nối" : "Mất kết nối"}</span><Link href="/" className="monitor-button">Chế độ tài xế</Link><Link href="/camera" className="monitor-button">Camera</Link></div></header>
    <div className="grid gap-4 lg:grid-cols-2"><div className="space-y-4"><VideoFeed active={connected}/><Controls disabled={!connected}/></div><div className="space-y-4">{telemetry ? <><RiskMeter score={telemetry.risk_score} level={telemetry.risk_level} muted={telemetry.muted}/><DriverStatus t={telemetry}/></> : <p className="monitor-panel monitor-empty">Đang chờ dữ liệu từ AI worker. Kiểm tra kết nối và camera.</p>}<EarMarChart history={history}/></div></div>
    <RiskTimeline points={points} events={events} now={now}/>
    <EventTable/>
    <SystemHealth telemetry={telemetry} connected={connected}/>
  </div></main>;
}
