"use client";

import { useCallback, useEffect, useState } from "react";
import { getEvents } from "@/lib/api";
import type { DriverEvent, RiskLevel } from "@/types/telemetry";
import { EventDrawer } from "./event-drawer";
import { eventNames, LevelMark } from "./monitor-ui";

export function EventTable() {
  const [events, setEvents] = useState<DriverEvent[]>([]);
  const [selected, setSelected] = useState<DriverEvent | null>(null);
  const [error, setError] = useState(false);
  const [loading, setLoading] = useState(true);
  const close = useCallback(() => setSelected(null), []);
  useEffect(() => {
    let alive = true;
    const load = async () => {
      try { const next = await getEvents(); if (alive) { setEvents(next); setError(false); } }
      catch { if (alive) setError(true); }
      finally { if (alive) setLoading(false); }
    };
    void load();
    const timer = setInterval(() => void load(), 3000);
    return () => { alive = false; clearInterval(timer); };
  }, []);
  return <section className="monitor-panel">
    <h2 className="monitor-panel-title">Sự kiện gần đây</h2>
    {error && <p role="alert" className="mb-3 text-[var(--danger,#b3261e)]">⚠ Không tải được sự kiện. Kiểm tra kết nối API; hệ thống sẽ thử lại.</p>}
    {loading ? <p className="text-[var(--text-muted,#5c5c57)]">Đang tải sự kiện…</p> : events.length === 0 ? <p className="text-[var(--text-muted,#5c5c57)]">Chưa có sự kiện. Tiếp tục theo dõi tài xế.</p> :
      <div className="max-h-80 overflow-auto"><table className="monitor-table"><thead><tr><th>Thời điểm</th><th>Loại</th><th>Mức</th><th className="monitor-number">Điểm</th><th>Chi tiết</th></tr></thead><tbody>{events.map((event, index) => {
        const level: RiskLevel = event.risk_level === "DANGER" ? "DANGER" : event.risk_level === "WARNING" ? "WARNING" : "NORMAL";
        return <tr key={event.id ?? `${event.started_at}-${index}`} onClick={() => setSelected(event)} onKeyDown={(key) => { if (key.key === "Enter" || key.key === " ") { key.preventDefault(); setSelected(event); } }} tabIndex={0} role="button" aria-label={`Xem chi tiết ${eventNames[event.event_type] ?? event.event_type} lúc ${new Date(event.started_at).toLocaleString("vi-VN")}`} className="monitor-event-row"><td className="p-3 tabular-nums">{new Date(event.started_at).toLocaleString("vi-VN")}</td><td className="p-3">{eventNames[event.event_type] ?? event.event_type}</td><td className="p-3"><LevelMark level={level}/></td><td className="p-3 monitor-number">{event.risk_score.toFixed(0)}</td><td className="p-3 text-[var(--accent,#1f5eff)] underline underline-offset-4">Xem</td></tr>;
      })}</tbody></table></div>}
    {selected && <EventDrawer event={selected} onClose={close}/>}
  </section>;
}
