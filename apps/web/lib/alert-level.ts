import type { RiskLevel } from "../types/telemetry";

export type AlertStage = "off" | "caution" | "danger" | "danger_escalated";

export interface AlertStageInput {
  level: RiskLevel;
  muted: boolean;
  connected: boolean;
  calibrated: boolean;
  dangerSinceMs: number | null;
  nowMs: number;
}

export interface BeepPatternConfig {
  frequencyHz: number;
  durationMs: number;
  intervalMs: number;
  volume: number;
}

export function alertStage(input: {
  level: RiskLevel;
  muted: boolean;
  connected: boolean;
  calibrated: boolean;
  dangerSinceMs: number | null;
  nowMs: number;
}): AlertStage {
  if (!input.connected || input.muted || !input.calibrated) {
    return "off";
  }

  if (input.level === "NORMAL") {
    return "off";
  }

  if (input.level === "WARNING") {
    return "caution";
  }

  if (input.level === "DANGER") {
    if (input.dangerSinceMs === null || input.nowMs - input.dangerSinceMs < 5000) {
      return "danger";
    }
    return "danger_escalated";
  }

  return "off";
}

export function beepPattern(
  stage: AlertStage
): { frequencyHz: number; durationMs: number; intervalMs: number; volume: number } | null {
  switch (stage) {
    case "caution":
      return {
        frequencyHz: 660,
        durationMs: 200,
        intervalMs: 4000,
        volume: 0.15,
      };
    case "danger":
      return {
        frequencyHz: 880,
        durationMs: 250,
        intervalMs: 1000,
        volume: 0.3,
      };
    case "danger_escalated":
      return {
        frequencyHz: 1100,
        durationMs: 300,
        intervalMs: 500,
        volume: 0.5,
      };
    case "off":
    default:
      return null;
  }
}
