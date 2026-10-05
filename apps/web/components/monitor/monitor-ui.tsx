import type { RiskLevel } from "@/types/telemetry";

export const eventNames: Record<string, string> = {
  DROWSINESS_ACUTE: "Buồn ngủ (nhắm mắt)", CHRONIC_FATIGUE: "Mệt mỏi tích lũy",
  LOOKING_AWAY: "Quay đầu lệch hướng", LOOKING_DOWN: "Cúi đầu",
  PHONE_USAGE: "Dùng điện thoại", DRIVER_ABSENCE: "Không thấy tài xế",
};

export function LevelMark({ level }: { level: RiskLevel }) {
  const label = { NORMAL: "Bình thường", WARNING: "Chú ý", DANGER: "Nguy hiểm" }[level];
  const color = { NORMAL: "var(--monitor-normal)", WARNING: "var(--monitor-warning)", DANGER: "var(--monitor-danger)" }[level];
  return <span className="inline-flex items-center gap-1 font-medium" style={{ color }}>
    <svg width="16" height="16" viewBox="0 0 20 20" fill="none" aria-hidden="true"><circle cx="10" cy="10" r="8" stroke="currentColor" strokeWidth="1.7"/><text x="10" y="14" textAnchor="middle" fill="currentColor" fontSize="12" fontWeight="bold">{level === "NORMAL" ? "✓" : level === "WARNING" ? "!" : "⚠"}</text></svg>
    {label}
  </span>;
}
