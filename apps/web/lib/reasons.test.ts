import test from "node:test";
import assert from "node:assert/strict";
import { activeReasons } from "./reasons.ts";
import type { Telemetry } from "../types/telemetry";

function makeTelemetry(overrides: Partial<Telemetry> = {}): Telemetry {
  return {
    timestamp: "2026-10-05T10:00:00Z",
    face_detected: true,
    calibrated: true,
    muted: false,
    ear: 0.3,
    mar: 0.2,
    yaw: 0,
    pitch: 0,
    roll: 0,
    relative_yaw: 0,
    relative_pitch: 0,
    eyes_closed: false,
    yawning: false,
    looking_away: false,
    looking_down: false,
    phone_detected: false,
    phone_usage: false,
    risk_score: 0,
    risk_level: "NORMAL",
    fps: { camera: 30, face: 30, phone: 30 },
    latency_ms: { face: 15, phone: 15 },
    events: [],
    ...overrides,
  };
}

test("activeReasons: returns empty list when all flags are false and face detected", () => {
  const t = makeTelemetry();
  assert.deepEqual(activeReasons(t), []);
});

test("activeReasons: returns individual reason with exact label", () => {
  assert.deepEqual(activeReasons(makeTelemetry({ eyes_closed: true })), [
    "Nhắm mắt kéo dài",
  ]);
  assert.deepEqual(activeReasons(makeTelemetry({ phone_usage: true })), [
    "Đang dùng điện thoại",
  ]);
  assert.deepEqual(activeReasons(makeTelemetry({ looking_away: true })), [
    "Quay đầu lệch hướng",
  ]);
  assert.deepEqual(activeReasons(makeTelemetry({ looking_down: true })), [
    "Cúi đầu",
  ]);
  assert.deepEqual(activeReasons(makeTelemetry({ yawning: true })), [
    "Ngáp",
  ]);
  assert.deepEqual(activeReasons(makeTelemetry({ face_detected: false })), [
    "Không thấy khuôn mặt",
  ]);
});

test("activeReasons: returns reasons in strict priority order when all flags are active", () => {
  const t = makeTelemetry({
    eyes_closed: true,
    phone_usage: true,
    looking_away: true,
    looking_down: true,
    yawning: true,
    face_detected: false,
  });

  const expected = [
    "Nhắm mắt kéo dài",
    "Đang dùng điện thoại",
    "Quay đầu lệch hướng",
    "Cúi đầu",
    "Ngáp",
    "Không thấy khuôn mặt",
  ];

  assert.deepEqual(activeReasons(t), expected);
});

test("activeReasons: maintains priority order with partial subsets of flags", () => {
  const t1 = makeTelemetry({
    yawning: true,
    eyes_closed: true,
  });
  assert.deepEqual(activeReasons(t1), ["Nhắm mắt kéo dài", "Ngáp"]);

  const t2 = makeTelemetry({
    looking_down: true,
    phone_usage: true,
    face_detected: false,
  });
  assert.deepEqual(activeReasons(t2), [
    "Đang dùng điện thoại",
    "Cúi đầu",
    "Không thấy khuôn mặt",
  ]);
});
