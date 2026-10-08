import type { Telemetry } from "../types/telemetry";

export function activeReasons(t: Telemetry): string[] {
  const reasons: string[] = [];

  if (t.eyes_closed) {
    reasons.push("Nhắm mắt kéo dài");
  }
  if (t.phone_usage) {
    reasons.push("Đang dùng điện thoại");
  }
  if (t.looking_away) {
    reasons.push("Quay đầu lệch hướng");
  }
  if (t.looking_down) {
    reasons.push("Cúi đầu");
  }
  if (t.yawning) {
    reasons.push("Ngáp");
  }
  if (!t.face_detected) {
    reasons.push("Không thấy khuôn mặt");
  }

  return reasons;
}
