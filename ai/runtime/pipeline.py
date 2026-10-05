"""Pipeline logic: quan sát (EAR/MAR/góc đầu/điện thoại) -> FSM -> rủi ro -> telemetry.

Không phụ thuộc camera hay mô hình; nhận quan sát đã tính sẵn nên test được bằng số liệu giả.
"""

from collections import deque
from dataclasses import dataclass
from datetime import datetime, timezone
from statistics import median
from typing import Any

from ai.perception.head_pose import NeutralPoseCalibrator, classify_head
from ai.risk.engine import RiskEngine
from ai.risk.rules import RiskLevel
from ai.runtime.thresholds import Thresholds
from ai.temporal.buffers import TimedBuffer
from ai.temporal.drowsiness import AlertState, DurationFSM

LEVEL_NAME = {RiskLevel.SAFE: "NORMAL", RiskLevel.WARNING: "WARNING", RiskLevel.DANGER: "DANGER"}

# Điểm rủi ro tức thời khi sự kiện ở trạng thái ACTIVE
INSTANT_RISK = {
    "DROWSINESS_ACUTE": 90.0,
    "LOOKING_AWAY": 65.0,
    "LOOKING_DOWN": 65.0,
    "PHONE_USAGE": 80.0,
    "DRIVER_ABSENCE": 60.0,
    "YAWNING": 45.0,
}


@dataclass
class FaceObservation:
    ear: float
    mar: float
    yaw: float
    pitch: float
    roll: float


@dataclass
class PhoneObservation:
    detected: bool = False
    usage_candidate: bool = False


def _iso(ts: float) -> str:
    return datetime.fromtimestamp(ts, tz=timezone.utc).isoformat()


class DriverPipeline:
    """Gom toàn bộ logic thời gian + rủi ro cho một phiên lái."""

    def __init__(self, thresholds: Thresholds | None = None) -> None:
        self.th = thresholds or Thresholds()
        t = self.th
        self.calibrator = NeutralPoseCalibrator(window_s=t.calibration_s)
        self.risk = RiskEngine()
        self.eyes_fsm = DurationFSM(t.eyes_closed_s, t.cooldown_s)
        self.yawn_fsm = DurationFSM(t.yawn_s, t.cooldown_s)
        self.away_fsm = DurationFSM(t.head_s, t.cooldown_s)
        self.down_fsm = DurationFSM(t.head_s, t.cooldown_s)
        self.phone_fsm = DurationFSM(t.phone_s, t.cooldown_s)
        self.absence_fsm = DurationFSM(t.absence_s, t.cooldown_s)
        self.eye_buffer = TimedBuffer(max_age_s=t.perclos_window_s)
        self._closed_samples: deque[tuple[float, bool]] = deque()
        self._yawns: deque[float] = deque()
        self._prev: dict[str, AlertState] = {}
        self._last_chronic = -1e9
        self._mute_until = 0.0
        self._started: dict[str, float] = {}
        self._ear_cal: list[float] = []
        self.ear_baseline: float | None = None

    # --- điều khiển ---
    def start_calibration(self) -> None:
        self.calibrator = NeutralPoseCalibrator(window_s=self.th.calibration_s)
        self._ear_cal = []
        self.ear_baseline = None

    @property
    def ear_threshold(self) -> float:
        """Ngưỡng nhắm mắt: 70% EAR lúc mở mắt bình thường của chính tài xế (kẹp 0.10-0.25)."""
        if self.ear_baseline is None:
            return self.th.ear_threshold
        return min(0.25, max(0.10, 0.7 * self.ear_baseline))

    def mute(self, now: float, duration_s: float) -> None:
        self._mute_until = now + duration_s

    # --- xử lý một nhịp ---
    def update(
        self, now: float, face: FaceObservation | None, phone: PhoneObservation | None = None
    ) -> tuple[dict[str, Any], list[dict[str, Any]]]:
        t = self.th
        phone = phone or PhoneObservation()
        events: list[dict[str, Any]] = []
        has_face = face is not None

        rel_yaw = rel_pitch = 0.0
        ear = mar = yaw = pitch = roll = 0.0
        eyes_closed_s = 0.0
        if face is not None:
            ear, mar, yaw, pitch, roll = face.ear, face.mar, face.yaw, face.pitch, face.roll
            pitch_signed = pitch * t.pitch_sign
            was_calibrated = self.calibrator.is_calibrated
            if not was_calibrated:
                self._ear_cal.append(ear)
            self.calibrator.add_sample(now, yaw, pitch_signed)
            if self.calibrator.is_calibrated and not was_calibrated and self._ear_cal:
                self.ear_baseline = float(median(self._ear_cal))
            if self.calibrator.is_calibrated:
                rel_yaw, rel_pitch = self.calibrator.relative(yaw, pitch_signed)
            self.eye_buffer.push(now, ear)
            eyes_closed_s = self.eye_buffer.duration_below(self.ear_threshold)
            self._closed_samples.append((now, ear < self.ear_threshold))
        else:
            self.eye_buffer.reset()
        while self._closed_samples and self._closed_samples[0][0] < now - t.perclos_window_s:
            self._closed_samples.popleft()

        calibrated = self.calibrator.is_calibrated
        head = classify_head(rel_yaw, rel_pitch, t.yaw_threshold, t.pitch_threshold)
        signals = {
            "DROWSINESS_ACUTE": has_face and ear < self.ear_threshold,
            "YAWNING": has_face and mar > t.mar_threshold,
            "LOOKING_AWAY": has_face and calibrated and head == "LOOKING_AWAY",
            "LOOKING_DOWN": has_face and calibrated and head == "LOOKING_DOWN",
            "PHONE_USAGE": phone.usage_candidate,
            "DRIVER_ABSENCE": not has_face,
        }
        fsms = {
            "DROWSINESS_ACUTE": self.eyes_fsm,
            "YAWNING": self.yawn_fsm,
            "LOOKING_AWAY": self.away_fsm,
            "LOOKING_DOWN": self.down_fsm,
            "PHONE_USAGE": self.phone_fsm,
            "DRIVER_ABSENCE": self.absence_fsm,
        }
        active: dict[str, bool] = {}
        newly: list[str] = []
        for name, fsm in fsms.items():
            state = fsm.update(now, bool(signals[name]))
            active[name] = state == AlertState.ACTIVE
            if state == AlertState.CANDIDATE and name not in self._started:
                self._started[name] = now
            if state == AlertState.IDLE:
                self._started.pop(name, None)
            if state == AlertState.ACTIVE and self._prev.get(name) != AlertState.ACTIVE:
                newly.append(name)
            self._prev[name] = state

        for name in newly:
            if name == "YAWNING":
                self._yawns.append(now)
        while self._yawns and self._yawns[0] < now - t.yawn_window_s:
            self._yawns.popleft()

        # Rủi ro mãn tính: PERCLOS + số lần ngáp
        perclos = 0.0
        span = self._closed_samples[-1][0] - self._closed_samples[0][0] if self._closed_samples else 0.0
        if span >= t.perclos_window_s / 2:  # chỉ tin PERCLOS khi đã quan sát đủ lâu
            perclos = sum(c for _, c in self._closed_samples) / len(self._closed_samples)
        chronic = min(70.0, perclos * 200.0 + len(self._yawns) * 10.0)

        instant = 0.0
        for name, is_active in active.items():
            if is_active:
                instant = max(instant, INSTANT_RISK[name])
        instant = max(instant, min(eyes_closed_s / t.eyes_closed_s, 1.0) * 70.0, chronic)

        state = self.risk.update(now, instant, eyes_closed_s)
        level = LEVEL_NAME[state.level]

        def make_event(event_type: str, reason: str, duration_s: float, confidence: float) -> dict:
            return {
                "event_type": event_type,
                "started_at": _iso(now - duration_s),
                "duration_ms": int(duration_s * 1000),
                "risk_score": round(state.score, 1),
                "risk_level": level,
                "confidence": confidence,
                "reason": reason,
            }

        reasons = {
            "DROWSINESS_ACUTE": ("Nhắm mắt kéo dài", t.eyes_closed_s),
            "LOOKING_AWAY": ("Quay đầu lệch hướng lái", t.head_s),
            "LOOKING_DOWN": ("Cúi đầu kéo dài", t.head_s),
            "PHONE_USAGE": ("Dùng điện thoại gần vùng mặt", t.phone_s),
            "DRIVER_ABSENCE": ("Không thấy khuôn mặt tài xế", t.absence_s),
        }
        for name in newly:
            if name in reasons:
                reason, dur = reasons[name]
                events.append(make_event(name, reason, dur, 0.9))
        if chronic >= 50.0 and now - self._last_chronic > 60.0:
            self._last_chronic = now
            events.append(
                make_event(
                    "CHRONIC_FATIGUE",
                    f"PERCLOS {perclos:.0%}, ngáp {len(self._yawns)} lần",
                    t.perclos_window_s,
                    0.7,
                )
            )

        telemetry = {
            "timestamp": _iso(now),
            "face_detected": has_face,
            "calibrated": calibrated,
            "muted": now < self._mute_until,
            "ear": round(ear, 3),
            "mar": round(mar, 3),
            "yaw": round(yaw, 1),
            "pitch": round(pitch, 1),
            "roll": round(roll, 1),
            "relative_yaw": round(rel_yaw, 1),
            "relative_pitch": round(rel_pitch, 1),
            "eyes_closed": active["DROWSINESS_ACUTE"],
            "yawning": active["YAWNING"],
            "looking_away": active["LOOKING_AWAY"],
            "looking_down": active["LOOKING_DOWN"],
            "phone_detected": phone.detected,
            "phone_usage": active["PHONE_USAGE"],
            "risk_score": round(state.score, 1),
            "risk_level": level,
            "fps": {"camera": 0, "face": 0, "phone": 0},
            "latency_ms": {"face": 0, "phone": 0},
            "events": events,
        }
        return telemetry, events
