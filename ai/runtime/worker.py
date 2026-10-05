"""AI Worker: tiến trình riêng đọc camera, chạy pipeline, đẩy telemetry/khung hình cho backend."""

import queue
import threading
import time
from typing import Any

import cv2
import numpy as np

from ai.runtime.metrics import FpsCounter
from ai.runtime.pipeline import DriverPipeline, FaceObservation, PhoneObservation
from ai.runtime.thresholds import load_thresholds

MAX_TELEMETRY_HZ = 15
LEVEL_COLOR = {"NORMAL": (80, 200, 80), "WARNING": (0, 200, 255), "DANGER": (60, 60, 240)}


def _put_latest(q: Any, item: Any) -> None:
    """Đẩy phần tử mới nhất; nếu đầy thì bỏ phần tử cũ."""
    while True:
        try:
            q.put_nowait(item)
            return
        except queue.Full:
            try:
                q.get_nowait()
            except queue.Empty:
                pass


def _draw_overlay(frame: np.ndarray, tele: dict, face_box: Any, phone_boxes: list) -> np.ndarray:
    color = LEVEL_COLOR.get(tele["risk_level"], (200, 200, 200))
    if face_box:
        cv2.rectangle(frame, face_box[:2], face_box[2:], color, 2)
    for b in phone_boxes:
        cv2.rectangle(frame, b[:2], b[2:], (255, 160, 0), 2)
    lines = [
        f"RISK {tele['risk_score']:.0f} {tele['risk_level']}",
        f"EAR {tele['ear']:.2f} MAR {tele['mar']:.2f}",
        f"yaw {tele['relative_yaw']:.0f} pitch {tele['relative_pitch']:.0f}"
        + ("" if tele["calibrated"] else " (calibrating)"),
    ]
    for i, text in enumerate(lines):
        cv2.putText(frame, text, (10, 24 + 22 * i), cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)
    return frame


def _encode(frame: np.ndarray) -> bytes | None:
    ok, buf = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 70])
    return buf.tobytes() if ok else None


class _Commands:
    """Đọc lệnh từ backend (không chặn)."""

    def __init__(self, command_q: Any, pipeline: DriverPipeline) -> None:
        self.q, self.pipeline, self.stop = command_q, pipeline, False

    def poll(self, now: float) -> None:
        while True:
            try:
                msg = self.q.get_nowait()
            except queue.Empty:
                return
            cmd = msg.get("cmd")
            if cmd == "calibrate":
                self.pipeline.start_calibration()
            elif cmd == "mute":
                self.pipeline.mute(now, float(msg.get("duration_seconds", 15)))
            elif cmd == "stop":
                self.stop = True


class _PhoneThread(threading.Thread):
    """Chạy YOLO ở ~5 FPS, tách khỏi vòng lặp khuôn mặt."""

    def __init__(self) -> None:
        super().__init__(daemon=True)
        self.frame: np.ndarray | None = None
        self.boxes: list = []
        self.updated = 0.0
        self.latency_ms = 0
        self.fps = FpsCounter()
        self.running = True
        self.error: str | None = None

    def run(self) -> None:
        try:
            from ai.perception.phone_detector import PhoneDetector

            detector = PhoneDetector()
        except Exception as exc:  # thiếu trọng số/GPU... : tắt phone, face vẫn chạy
            self.error = str(exc)
            return
        while self.running:
            frame = self.frame
            if frame is None:
                time.sleep(0.05)
                continue
            start = time.time()
            self.boxes = detector.detect(frame)
            self.updated = time.time()
            self.latency_ms = int((self.updated - start) * 1000)
            self.fps.tick(self.updated)
            time.sleep(max(0.0, 0.2 - (time.time() - start)))


def _run_camera(telemetry_q: Any, command_q: Any, frame_q: Any, config: dict) -> None:
    from ai.perception.face_landmarks import FaceLandmarkTracker
    from ai.perception.phone_detector import FaceBoxHold, is_usage_region

    pipeline = DriverPipeline(load_thresholds())
    cmds = _Commands(command_q, pipeline)
    tracker = FaceLandmarkTracker()
    phone_thread = _PhoneThread()
    if config.get("enable_phone", True):
        phone_thread.start()
    cam_fps, face_fps = FpsCounter(), FpsCounter()
    face_hold = FaceBoxHold(2.0)
    pending_events: list[dict] = []
    last_sent = 0.0
    cap = None

    while not cmds.stop:
        now = time.time()
        cmds.poll(now)
        if cap is None or not cap.isOpened():
            cap = cv2.VideoCapture(int(config.get("camera_index", 0)), cv2.CAP_DSHOW)
            cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
            if not cap.isOpened():
                _put_latest(telemetry_q, {"error": "camera_unavailable", "face_detected": False,
                                          "events": [], "risk_level": "NORMAL", "risk_score": 0.0})
                time.sleep(2.0)
                continue
        ok, frame = cap.read()
        if not ok:
            time.sleep(0.05)
            continue
        cam_fps.tick(now)
        phone_thread.frame = frame

        t0 = time.time()
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        obs, face_box, _ = tracker.process(rgb, now)
        face_ms = int((time.time() - t0) * 1000)
        face_fps.tick(now)

        roi_box = face_hold.update(now, face_box)
        recent = time.time() - phone_thread.updated < 1.0
        boxes = phone_thread.boxes if recent else []
        phone = PhoneObservation(
            detected=bool(boxes),
            usage_candidate=any(is_usage_region(b, roi_box) for b in boxes),
        )
        tele, events = pipeline.update(now, obs, phone)
        tele["fps"] = {"camera": cam_fps.value(now), "face": face_fps.value(now),
                       "phone": phone_thread.fps.value(now)}
        tele["latency_ms"] = {"face": face_ms, "phone": phone_thread.latency_ms}
        pending_events.extend(events)

        _put_latest(frame_q, _encode(_draw_overlay(frame, tele, face_box, boxes)))
        if now - last_sent >= 1.0 / MAX_TELEMETRY_HZ or pending_events:
            tele["events"] = pending_events
            pending_events = []
            last_sent = now
            _put_latest(telemetry_q, tele)

    phone_thread.running = False
    if cap is not None:
        cap.release()
    tracker.close()


# Kịch bản mô phỏng: (số giây, mô tả, hàm tạo quan sát)
def _scenario(t: float) -> tuple[FaceObservation | None, PhoneObservation]:
    cycle = t % 40.0
    base = FaceObservation(ear=0.30, mar=0.20, yaw=0.0, pitch=0.0, roll=0.0)
    if 15 <= cycle < 19:  # nhắm mắt
        base.ear = 0.10
    elif 24 <= cycle < 28:  # quay đầu
        base.yaw = 45.0
    elif 31 <= cycle < 34:  # dùng điện thoại
        return base, PhoneObservation(detected=True, usage_candidate=True)
    elif 36 <= cycle < 38:  # ngáp
        base.mar = 0.8
    return base, PhoneObservation()


def _run_simulated(telemetry_q: Any, command_q: Any, frame_q: Any, config: dict) -> None:
    pipeline = DriverPipeline(load_thresholds())
    cmds = _Commands(command_q, pipeline)
    start = time.time()
    while not cmds.stop:
        now = time.time()
        cmds.poll(now)
        obs, phone = _scenario(now - start)
        tele, _ = pipeline.update(now, obs, phone)
        tele["fps"] = {"camera": 10, "face": 10, "phone": 5}
        tele["latency_ms"] = {"face": 5, "phone": 20}
        _put_latest(telemetry_q, tele)
        frame = np.zeros((480, 640, 3), np.uint8)
        cv2.putText(frame, "SIMULATION", (200, 240), cv2.FONT_HERSHEY_SIMPLEX, 1.2, (200, 200, 200), 2)
        jpg = _encode(_draw_overlay(frame, tele, None, []))
        if jpg:
            _put_latest(frame_q, jpg)
        time.sleep(0.1)


def run_worker(telemetry_q: Any, command_q: Any, frame_q: Any, config: dict | None = None) -> None:
    """Điểm vào của tiến trình AI Worker (xem docs/mvp-contract.md)."""
    config = config or {}
    try:
        if config.get("simulate"):
            _run_simulated(telemetry_q, command_q, frame_q, config)
        else:
            _run_camera(telemetry_q, command_q, frame_q, config)
    finally:
        # Không chờ backend đọc nốt hàng đợi khi thoát (tránh treo tiến trình)
        for q in (telemetry_q, frame_q):
            q.cancel_join_thread()
