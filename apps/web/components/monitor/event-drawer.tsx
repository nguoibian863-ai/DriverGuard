"use client";

import { useEffect, useRef } from "react";
import type { DriverEvent, RiskLevel } from "@/types/telemetry";
import { eventNames, LevelMark } from "./monitor-ui";

export function EventDrawer({ event, onClose }: { event: DriverEvent; onClose: () => void }) {
  const dialog = useRef<HTMLElement>(null);
  const close = useRef<HTMLButtonElement>(null);
  useEffect(() => {
    const previous = document.activeElement instanceof HTMLElement ? document.activeElement : null;
    close.current?.focus();
    const handle = (key: KeyboardEvent) => {
      if (key.key === "Escape") onClose();
      if (key.key !== "Tab" || !dialog.current) return;
      const focusable = Array.from(dialog.current.querySelectorAll<HTMLElement>('button, a[href], [tabindex]:not([tabindex="-1"])')).filter((item) => !item.hasAttribute("disabled"));
      if (!focusable.length) return;
      const first = focusable[0], last = focusable[focusable.length - 1];
      if (key.shiftKey && document.activeElement === first) { key.preventDefault(); last.focus(); }
      else if (!key.shiftKey && document.activeElement === last) { key.preventDefault(); first.focus(); }
    };
    document.addEventListener("keydown", handle);
    return () => { document.removeEventListener("keydown", handle); previous?.focus(); };
  }, [onClose]);
  const level: RiskLevel = event.risk_level === "DANGER" ? "DANGER" : event.risk_level === "WARNING" ? "WARNING" : "NORMAL";
  const fields = [
    ["Thời điểm", new Date(event.started_at).toLocaleString("vi-VN")],
    ["Thời lượng", `${(event.duration_ms / 1000).toFixed(1)} giây`],
    ["Điểm rủi ro", event.risk_score.toFixed(0)],
    ["Độ tin cậy", `${(event.confidence * 100).toFixed(0)}%`],
    ["Nguyên nhân", event.reason || "Chưa có mô tả nguyên nhân."],
  ];
  return <div className="fixed inset-0 z-50 flex justify-end bg-black/70" onMouseDown={(mouse) => { if (mouse.target === mouse.currentTarget) onClose(); }}>
    <aside ref={dialog} role="dialog" aria-modal="true" aria-labelledby="event-title" className="h-full w-full max-w-md overflow-y-auto border-l border-[var(--monitor-border)] bg-[var(--monitor-surface)] p-6 text-[var(--monitor-text)] shadow-2xl">
      <div className="flex items-start justify-between gap-4"><div><p className="text-sm text-[var(--monitor-muted)]">Chi tiết sự kiện</p><h2 id="event-title" className="mt-1 text-xl font-semibold">{eventNames[event.event_type] ?? event.event_type}</h2></div><button ref={close} type="button" onClick={onClose} aria-label="Đóng chi tiết sự kiện" className="monitor-action rounded-[var(--monitor-radius)] border border-[var(--monitor-border)] px-4">Đóng</button></div>
      <div className="mt-6 border-b border-[var(--monitor-border)] pb-4"><p className="text-sm text-[var(--monitor-muted)]">Mức</p><LevelMark level={level}/></div>
      <dl className="mt-4 space-y-5">{fields.map(([label, value]) => <div key={label}><dt className="text-sm text-[var(--monitor-muted)]">{label}</dt><dd className="mt-1 break-words">{value}</dd></div>)}</dl>
    </aside>
  </div>;
}
