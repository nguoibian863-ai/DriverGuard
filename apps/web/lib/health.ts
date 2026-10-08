import { API_URL } from "./api";

export interface Health {
  status: string;
  ai_worker_alive: boolean;
  camera_connected: boolean;
}

export async function getHealth(): Promise<Health> {
  const response = await fetch(`${API_URL}/api/v1/health`, { cache: "no-store" });
  if (!response.ok) throw new Error(`health ${response.status}`);
  return response.json() as Promise<Health>;
}
