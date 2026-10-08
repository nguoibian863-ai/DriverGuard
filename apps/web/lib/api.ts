import type { DriverEvent } from "@/types/telemetry";

export const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
export const WS_URL = API_URL.replace(/^http/, "ws") + "/ws/status";

export async function getEvents(limit = 50): Promise<DriverEvent[]> {
  const res = await fetch(`${API_URL}/api/v1/events?limit=${limit}`, { cache: "no-store" });
  if (!res.ok) throw new Error(`events ${res.status}`);
  const data = await res.json();
  return data.events as DriverEvent[];
}

export async function postCalibrate(): Promise<void> {
  await fetch(`${API_URL}/api/v1/sessions/calibrate`, { method: "POST" });
}

export async function postMute(durationSeconds = 15): Promise<void> {
  await fetch(`${API_URL}/api/v1/alerts/mute`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ duration_seconds: durationSeconds }),
  });
}
