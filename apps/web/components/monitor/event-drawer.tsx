"use client";

import { useEffect, useRef, useState } from "react";
import { eventSnapshotUrl } from "@/lib/api";
import type { DriverEvent, RiskLevel } from "@/types/telemetry";
import { eventNames, LevelMark } from "./monitor-ui";

export function EventDrawer({ event, onClose }: { event: DriverEvent; onClose: () => void }) {
  const dialog = useRef<HTMLElement>(null);
  const close = useRef<HTMLButtonElement>(null);
  // Ảnh có thể đã bị dọn theo FIFO: ẩn khung ảnh thay vì hiện ảnh vỡ.
  // Lưu id đã lỗi (không dùng cờ + effect reset) để đổi sự kiện là tự hiện lại.
  const [failedSnapshotId, setFailedSnapshotId] = useState<string | null>(null);
  const snapshotFailed = failedSnapshotId !== null && failedSnapshotId === event.id;
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
    <aside ref={dialog} role="dialog" aria-modal="true" aria-labelledby="event-title" className="h-full w-full max-w-md overflow-y-auto border-l border-[var(--border,#d9d9d4)] bg-[var(--surface,#fff)] p-6 text-[var(--text,#1a1a18)]">
      <div className="flex items-start justify-between gap-4"><div><p className="text-sm text-[var(--text-muted,#5c5c57)]">Chi tiết sự kiện</p><h2 id="event-title" className="mt-1 text-xl font-semibold">{eventNames[event.event_type] ?? event.event_type}</h2></div><button ref={close} type="button" onClick={onClose} aria-label="Đóng chi tiết sự kiện" className="monitor-button">Đóng</button></div>
      <div className="mt-6 border-b border-[var(--border,#d9d9d4)] pb-4"><p className="text-sm text-[var(--text-muted,#5c5c57)]">Mức</p><LevelMark level={level}/></div>
      {event.id && event.snapshot_path && !snapshotFailed && (
        <figure className="mt-4">
          <figcaption className="text-sm text-[var(--text-muted,#5c5c57)]">Ảnh lúc xảy ra</figcaption>
          {/* Ảnh chạy thời gian thực từ backend cấu hình được; không qua tối ưu ảnh của Next */}
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img
            src={eventSnapshotUrl(event.id)}
            alt={`Ảnh chụp lúc ${eventNames[event.event_type] ?? event.event_type}`}
            onError={() => setFailedSnapshotId(event.id ?? null)}
            className="mt-2 w-full border border-[var(--border,#d9d9d4)] object-contain"
          />
        </figure>
      )}
      <dl className="mt-4 space-y-5">{fields.map(([label, value]) => <div key={label}><dt className="text-sm text-[var(--text-muted,#5c5c57)]">{label}</dt><dd className="mt-1 break-words">{value}</dd></div>)}</dl>
    </aside>
  </div>;
}
