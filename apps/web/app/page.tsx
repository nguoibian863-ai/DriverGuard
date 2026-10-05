"use client";

import { EarMarChart } from "@/components/charts/ear-mar-chart";
import { Controls } from "@/components/controls/controls";
import { DriverStatus } from "@/components/driver-status/driver-status";
import { EventList } from "@/components/event-list/event-list";
import { RiskMeter } from "@/components/risk-meter/risk-meter";
import { VideoFeed } from "@/components/video-feed/video-feed";
import { useTelemetry } from "@/lib/useTelemetry";

export default function Home() {
  const { telemetry, connected, history } = useTelemetry();

  return (
    <main className="mx-auto w-full max-w-6xl space-y-4 p-4 sm:p-6">
      <header className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold">DriverGuard</h1>
          <p className="text-sm text-zinc-500">Giám sát tài xế theo thời gian thực</p>
        </div>
        <span
          className={`rounded-full px-3 py-1 text-xs font-medium ${
            connected ? "bg-emerald-100 text-emerald-700" : "bg-red-100 text-red-700"
          }`}
        >
          {connected ? "Đã kết nối" : "Mất kết nối — đang thử lại…"}
        </span>
      </header>

      <div className="grid gap-4 lg:grid-cols-2">
        <div className="space-y-4">
          <VideoFeed active={connected} />
          <Controls disabled={!connected} />
        </div>
        <div className="space-y-4">
          {telemetry ? (
            <>
              <RiskMeter score={telemetry.risk_score} level={telemetry.risk_level} muted={telemetry.muted} />
              <DriverStatus t={telemetry} />
            </>
          ) : (
            <p className="rounded-xl border border-dashed border-zinc-300 p-6 text-center text-sm text-zinc-500">
              Đang chờ dữ liệu từ AI worker…
            </p>
          )}
          <EarMarChart history={history} />
        </div>
      </div>

      <EventList />
    </main>
  );
}
