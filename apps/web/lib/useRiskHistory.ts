"use client";

import { useEffect, useState } from "react";
import type { Telemetry } from "@/types/telemetry";
import { downsample, pruneOlderThan, type TimelinePoint } from "./timeline";

export interface TimelineEvent { key: string; time: number; eventType: string; score: number }
const WINDOW_MS = 300_000;

export function useRiskHistory(telemetry: Telemetry | null) {
  const [points, setPoints] = useState<TimelinePoint[]>([]);
  const [events, setEvents] = useState<TimelineEvent[]>([]);

  useEffect(() => {
    if (!telemetry) return;
    const now = Date.now();
    const timer = setTimeout(() => { setPoints((previous) => {
      const recent = pruneOlderThan(previous, now, WINDOW_MS);
      if (recent.length && now - recent[recent.length - 1].time < 1000) return recent;
      return downsample([...recent, { time: now, score: telemetry.risk_score }], 300);
    });
    setEvents((previous) => {
      const recent = pruneOlderThan(previous, now, WINDOW_MS);
      const known = new Set(recent.map((event) => event.key));
      const incoming: TimelineEvent[] = [];
      for (const event of telemetry.events) {
        const parsed = Date.parse(event.started_at);
        const time = Number.isFinite(parsed) ? parsed : now;
        const key = String(event.id ?? `${event.event_type}:${event.started_at}`);
        if (time >= now - WINDOW_MS && time <= now && !known.has(key)) {
          incoming.push({ key, time, eventType: event.event_type, score: event.risk_score });
          known.add(key);
        }
      }
      return [...recent, ...incoming];
    }); }, 0);
    return () => clearTimeout(timer);
  }, [telemetry]);

  useEffect(() => {
    const timer = setInterval(() => {
      const now = Date.now();
      setPoints((previous) => pruneOlderThan(previous, now, WINDOW_MS));
      setEvents((previous) => pruneOlderThan(previous, now, WINDOW_MS));
    }, 5000);
    return () => clearInterval(timer);
  }, []);

  return { points, events };
}
