"use client";

import { useEffect, useState } from "react";
import { getEvents } from "@/lib/api";
import type { DriverEvent } from "@/types/telemetry";

const NAMES: Record<string, string> = {
  DROWSINESS_ACUTE: "Buồn ngủ (nhắm mắt)",
  CHRONIC_FATIGUE: "Mệt mỏi tích lũy",
  LOOKING_AWAY: "Quay đầu lệch hướng",
  LOOKING_DOWN: "Cúi đầu",
  PHONE_USAGE: "Dùng điện thoại",
  DRIVER_ABSENCE: "Không thấy tài xế",
};

export function EventList() {
  const [events, setEvents] = useState<DriverEvent[]>([]);
  const [error, setError] = useState(false);

  useEffect(() => {
    let alive = true;
    const load = async () => {
      try {
        const e = await getEvents(50);
        if (alive) {
          setEvents(e);
          setError(false);
        }
      } catch {
        if (alive) setError(true);
      }
    };
    load();
    const id = setInterval(load, 3000);
    return () => {
      alive = false;
      clearInterval(id);
    };
  }, []);

  return (
    <section className="rounded-xl border border-zinc-200 p-4 dark:border-zinc-800">
      <h2 className="mb-3 text-sm font-medium text-zinc-500">Lịch sử sự kiện</h2>
      {error && <p className="text-sm text-red-600">Không tải được sự kiện.</p>}
      {events.length === 0 && !error ? (
        <p className="text-sm text-zinc-500">Chưa có sự kiện nào.</p>
      ) : (
        <div className="max-h-72 overflow-auto">
          <table className="w-full text-left text-sm">
            <thead className="sticky top-0 bg-white text-xs text-zinc-500 dark:bg-zinc-950">
              <tr>
                <th className="py-1 pr-3">Thời điểm</th>
                <th className="pr-3">Loại</th>
                <th className="pr-3">Mức</th>
                <th>Điểm</th>
              </tr>
            </thead>
            <tbody>
              {events.map((e, i) => (
                <tr key={e.id ?? i} className="border-t border-zinc-100 dark:border-zinc-900">
                  <td className="py-1 pr-3 tabular-nums">{new Date(e.started_at).toLocaleTimeString("vi-VN")}</td>
                  <td className="pr-3" title={e.reason}>
                    {NAMES[e.event_type] ?? e.event_type}
                  </td>
                  <td className={`pr-3 font-medium ${e.risk_level === "DANGER" ? "text-red-600" : "text-amber-600"}`}>
                    {e.risk_level}
                  </td>
                  <td className="tabular-nums">{e.risk_score.toFixed(0)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}
