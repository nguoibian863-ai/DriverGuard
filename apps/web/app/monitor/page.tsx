"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { EarMarChart } from "@/components/charts/ear-mar-chart";
import { Controls } from "@/components/controls/controls";
import { DriverStatus } from "@/components/driver-status/driver-status";
import { EventList } from "@/components/event-list/event-list";
import { RiskMeter } from "@/components/risk-meter/risk-meter";
import { VideoFeed } from "@/components/video-feed/video-feed";
import { EventTable } from "@/components/monitor/event-table";
import { RiskTimeline } from "@/components/monitor/risk-timeline";
import { SystemHealth } from "@/components/monitor/system-health";
import { useTelemetry } from "@/lib/useTelemetry";
import { useRiskHistory } from "@/lib/useRiskHistory";
import { LevelMark } from "@/components/monitor/monitor-ui";
import "./monitor.css";

export default function MonitorPage() {
  const { telemetry, connected, history } = useTelemetry();
  const { points, events } = useRiskHistory(telemetry);
  const [now, setNow] = useState(0);
  useEffect(() => { const update = () => setNow(Date.now()); update(); const timer = setInterval(update, 1000); return () => clearInterval(timer); }, []);
  return <main className="monitor-page"><div className="mx-auto w-full max-w-7xl space-y-4 p-4 sm:p-6">
    <header className="flex flex-wrap items-center justify-between gap-4"><div><h1 className="text-2xl font-bold">DriverGuard · Giám sát</h1><p className="text-sm text-[var(--monitor-muted)]">Theo dõi tài xế theo thời gian thực</p></div><div className="flex flex-wrap items-center gap-4"><span className="text-sm"><LevelMark level={connected ? "NORMAL" : "DANGER"}/> · {connected ? "WebSocket đã kết nối" : "Mất kết nối, đang thử lại"}</span><Link href="/" className="monitor-action rounded-[var(--monitor-radius)] border border-[var(--monitor-border)] px-4 text-sm text-[var(--monitor-link)]">Chế độ tài xế</Link></div></header>
    <div className="grid gap-4 lg:grid-cols-2"><div className="space-y-4"><VideoFeed active={connected}/><Controls disabled={!connected}/></div><div className="space-y-4">{telemetry ? <><RiskMeter score={telemetry.risk_score} level={telemetry.risk_level} muted={telemetry.muted}/><DriverStatus t={telemetry}/></> : <p className="rounded-[var(--monitor-radius)] border border-[var(--monitor-border)] p-6 text-center text-[var(--monitor-muted)]">Đang chờ dữ liệu từ AI worker. Kiểm tra kết nối và camera.</p>}<EarMarChart history={history}/></div></div>
    <RiskTimeline points={points} events={events} now={now}/>
    <EventTable/>
    <SystemHealth telemetry={telemetry} connected={connected}/>
    <details className="text-sm text-[var(--monitor-muted)]"><summary className="monitor-action cursor-pointer">Danh sách sự kiện cũ</summary><EventList/></details>
  </div></main>;
}
