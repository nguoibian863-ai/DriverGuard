import test from "node:test";
import assert from "node:assert/strict";
import { alertStage, beepPattern } from "./alert-level.ts";

test("alertStage: returns 'off' when not connected", () => {
  const result = alertStage({
    level: "DANGER",
    muted: false,
    connected: false,
    calibrated: true,
    dangerSinceMs: 1000,
    nowMs: 7000,
  });
  assert.equal(result, "off");
});

test("alertStage: returns 'off' when muted", () => {
  const result = alertStage({
    level: "DANGER",
    muted: true,
    connected: true,
    calibrated: true,
    dangerSinceMs: 1000,
    nowMs: 7000,
  });
  assert.equal(result, "off");
});

test("alertStage: returns 'off' when not calibrated", () => {
  const result = alertStage({
    level: "DANGER",
    muted: false,
    connected: true,
    calibrated: false,
    dangerSinceMs: 1000,
    nowMs: 7000,
  });
  assert.equal(result, "off");
});

test("alertStage: returns 'off' for NORMAL level", () => {
  const result = alertStage({
    level: "NORMAL",
    muted: false,
    connected: true,
    calibrated: true,
    dangerSinceMs: null,
    nowMs: 1000,
  });
  assert.equal(result, "off");
});

test("alertStage: returns 'caution' for WARNING level", () => {
  const result = alertStage({
    level: "WARNING",
    muted: false,
    connected: true,
    calibrated: true,
    dangerSinceMs: null,
    nowMs: 1000,
  });
  assert.equal(result, "caution");
});

test("alertStage: returns 'danger' when dangerSinceMs is null", () => {
  const result = alertStage({
    level: "DANGER",
    muted: false,
    connected: true,
    calibrated: true,
    dangerSinceMs: null,
    nowMs: 1000,
  });
  assert.equal(result, "danger");
});

test("alertStage: returns 'danger' when duration is strictly less than 5000ms", () => {
  const result = alertStage({
    level: "DANGER",
    muted: false,
    connected: true,
    calibrated: true,
    dangerSinceMs: 10000,
    nowMs: 14999,
  });
  assert.equal(result, "danger");
});

test("alertStage: returns 'danger_escalated' at exactly 5000ms mark", () => {
  const result = alertStage({
    level: "DANGER",
    muted: false,
    connected: true,
    calibrated: true,
    dangerSinceMs: 10000,
    nowMs: 15000,
  });
  assert.equal(result, "danger_escalated");
});

test("alertStage: returns 'danger_escalated' after 5000ms", () => {
  const result = alertStage({
    level: "DANGER",
    muted: false,
    connected: true,
    calibrated: true,
    dangerSinceMs: 10000,
    nowMs: 17500,
  });
  assert.equal(result, "danger_escalated");
});

test("beepPattern: returns expected configs for all stages", () => {
  assert.equal(beepPattern("off"), null);

  assert.deepEqual(beepPattern("caution"), {
    frequencyHz: 660,
    durationMs: 200,
    intervalMs: 4000,
    volume: 0.15,
  });

  assert.deepEqual(beepPattern("danger"), {
    frequencyHz: 880,
    durationMs: 250,
    intervalMs: 1000,
    volume: 0.3,
  });

  assert.deepEqual(beepPattern("danger_escalated"), {
    frequencyHz: 1100,
    durationMs: 300,
    intervalMs: 500,
    volume: 0.5,
  });
});
