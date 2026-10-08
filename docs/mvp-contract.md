# MVP Contract - AI Worker <-> Backend <-> Web

Hợp đồng chung cho 3 phần làm song song. KHÔNG tự ý đổi tên khóa.

## 1. Tiến trình
- Backend (FastAPI, cổng 8000) khởi động AI Worker bằng `multiprocessing.get_context("spawn")`:
  `ai.runtime.worker.run_worker(telemetry_q, command_q, frame_q, config)`.
- `telemetry_q`: worker -> backend, mỗi phần tử là `dict` telemetry (mục 2). Tối đa ~15 phần tử/giây.
- `frame_q` (maxsize=2): worker -> backend, phần tử là `bytes` JPEG của khung hình mới nhất (đã vẽ overlay).
- `command_q`: backend -> worker, phần tử là `dict`:
  - `{"cmd": "calibrate"}`
  - `{"cmd": "mute", "duration_seconds": 15}`
  - `{"cmd": "stop"}`
- `config` (dict): `{"simulate": bool, "camera_index": int, "enable_phone": bool}`.
  `simulate=True` => worker phát telemetry giả lập (không cần camera) để test.
- Biến môi trường backend: `DRIVERGUARD_START_WORKER` (mặc định "1"; test đặt "0"),
  `DRIVERGUARD_SIMULATE` (mặc định "0"), `DRIVERGUARD_DB` (đường dẫn SQLite, mặc định `data/driverguard.db`).

## 2. Telemetry dict
```json
{
  "timestamp": "2026-10-05T08:00:00.120+00:00",
  "face_detected": true,
  "calibrated": false,
  "muted": false,
  "ear": 0.23, "mar": 0.31,
  "yaw": 12.4, "pitch": -3.2, "roll": 1.1,
  "relative_yaw": 4.2, "relative_pitch": -1.3,
  "eyes_closed": false, "yawning": false,
  "looking_away": false, "looking_down": false,
  "phone_detected": false, "phone_usage": false,
  "risk_score": 18.0,
  "risk_level": "NORMAL",
  "fps": {"camera": 30, "face": 29, "phone": 5},
  "latency_ms": {"face": 12, "phone": 43},
  "events": []
}
```
- `risk_level` thuộc `NORMAL | WARNING | DANGER`.
- `events`: danh sách sự kiện MỚI phát sinh ở nhịp này (thường rỗng). Mỗi sự kiện:
  `{"event_type": "DROWSINESS_ACUTE", "started_at": "<iso>", "duration_ms": 1800, "risk_score": 85.0, "risk_level": "DANGER", "confidence": 0.9, "reason": "..."}`
- `event_type` thuộc: `DROWSINESS_ACUTE, CHRONIC_FATIGUE, LOOKING_AWAY, LOOKING_DOWN, PHONE_USAGE, DRIVER_ABSENCE`.

## 3. REST/WebSocket (backend)
- `GET  /api/v1/health` -> `{"status","ai_worker_alive","camera_connected"}`
- `WS   /ws/status` -> broadcast telemetry dict (JSON) cho mọi client.
- `GET  /api/v1/video/stream?overlay=true` -> `multipart/x-mixed-replace; boundary=frame` (MJPEG từ `frame_q`).
- `POST /api/v1/sessions/calibrate` -> đẩy `{"cmd":"calibrate"}`, trả `{"ok": true}`.
- `POST /api/v1/alerts/mute` body `{"duration_seconds": 15}` -> đẩy lệnh mute, trả `{"ok": true}`.
- `GET  /api/v1/events?limit=50` -> `{"events": [ {id, session_id, event_type, started_at, duration_ms, risk_score, risk_level, confidence, reason} ]}` mới nhất trước.
- `GET  /api/v1/config` -> ngưỡng hiện tại (dict).
- Mọi `events` trong telemetry phải được lưu vào SQLite (bảng `events`, `sessions`).
- CORS cho `http://localhost:3000`.

## 4. Web (Next.js, cổng 3000)
- Kết nối `ws://localhost:8000/ws/status`, gọi REST ở `http://localhost:8000` (đọc từ `NEXT_PUBLIC_API_URL`, mặc định đó).
