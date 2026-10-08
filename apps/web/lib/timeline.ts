import type { RiskLevel } from "../types/telemetry.ts";

export interface TimelinePoint { time: number; score: number }

export function downsample<T>(points: readonly T[], maxPoints: number): T[] {
  const limit = Math.floor(maxPoints);
  if (limit <= 0) return [];
  if (points.length <= limit) return [...points];
  if (limit === 1) return [points[points.length - 1]];
  return Array.from({ length: limit }, (_, i) => points[Math.round(i * (points.length - 1) / (limit - 1))]);
}

export function pruneOlderThan<T extends { time: number }>(points: readonly T[], nowMs: number, windowMs: number): T[] {
  return points.filter((point) => point.time >= nowMs - windowMs && point.time <= nowMs);
}

export function levelBand(score: number): RiskLevel {
  if (score >= 70) return "DANGER";
  if (score >= 40) return "WARNING";
  return "NORMAL";
}
