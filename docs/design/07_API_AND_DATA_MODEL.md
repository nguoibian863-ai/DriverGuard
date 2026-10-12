# API & Data Model

# 1. REST API Chi Tiết

## 1.1 Health Check
```http
GET /api/v1/health
```
Response:
```json
{
  "status": "ok",
  "ai_worker_alive": true,
  "camera_connected": true
}
```

## 1.2 Video Streaming (MJPEG)
```http
GET /api/v1/video/stream?overlay=true
```
- **Content-Type**: `multipart/x-mixed-replace; boundary=frame`
- Đọc khung hình trực tiếp từ Shared Memory / Latest Frame Buffer.
- Hỗ trợ tham số `overlay=true/false` để bật/tắt vẽ landmark và bounding box.

## 1.3 Quản Lý Phiên Lái (Sessions) & Hiệu Chuẩn (Calibration)
```http
POST /api/v1/sessions
GET  /api/v1/sessions
GET  /api/v1/sessions/{session_id}
POST /api/v1/sessions/{session_id}/stop
POST /api/v1/sessions/calibrate
```
* `POST /api/v1/sessions/calibrate`: Kích hoạt cửa sổ hiệu chuẩn 3–5 giây để tính median $(yaw_0, pitch_0)$ làm mốc neutral pose.

## 1.4 Quản Lý Cảnh Báo (Alert Control)
```http
POST /api/v1/alerts/mute
```
* Request body: `{"duration_seconds": 15}` — Tắt âm cảnh báo trong khoảng thời gian chỉ định để tránh gây hoảng loạn (Alert Fatigue).

## 1.5 Events & Cấu Hình
```http
GET /api/v1/events
GET /api/v1/events/{event_id}
GET /api/v1/config
PUT /api/v1/config
```

---

# 2. WebSocket Telemetry (`/ws/status`)

Được broadcast thời gian thực từ FastAPI sau khi nhận telemetry từ AI Worker qua `multiprocessing.Queue`:

```json
{
  "timestamp": "2026-10-04T21:50:00.120Z",
  "face_detected": true,
  "ear": 0.23,
  "mar": 0.31,
  "yaw": 12.4,
  "pitch": -3.2,
  "roll": 1.1,
  "relative_yaw": 4.2,
  "relative_pitch": -1.3,
  "eyes_closed": false,
  "yawning": false,
  "looking_away": false,
  "phone_detected": false,
  "phone_usage": false,
  "risk_score": 18,
  "risk_level": "NORMAL",
  "fps": {
    "camera": 30,
    "face": 29,
    "phone": 5
  },
  "latency_ms": {
    "face": 12,
    "phone": 43
  }
}
```

---

# 3. Data Model (SQLite)

## Session
```text
id               INTEGER PRIMARY KEY
started_at       DATETIME
ended_at         DATETIME
status           TEXT (ACTIVE, COMPLETED)
neutral_yaw      REAL
neutral_pitch    REAL
event_count      INTEGER
average_risk     REAL
max_risk         REAL
```

## Event
```text
id               INTEGER PRIMARY KEY
session_id       INTEGER (FK -> Session.id)
event_type       TEXT
started_at       DATETIME
ended_at         DATETIME
duration_ms      INTEGER
risk_score       REAL
risk_level       TEXT (WARNING, DANGER)
confidence       REAL
reason           TEXT
snapshot_path    TEXT (nullable)
```

## Event Types
```text
DROWSINESS_ACUTE      (Nhắm mắt kéo dài > 1.8s)
CHRONIC_FATIGUE       (PERCLOS cao, ngáp lặp lại)
LOOKING_AWAY          (Quay đầu / nhìn lệch hướng lái)
LOOKING_DOWN          (Cúi đầu kéo dài)
PHONE_USAGE           (Sử dụng điện thoại trên tay)
DRIVER_ABSENCE        (Không tìm thấy khuôn mặt)
```

---

# 4. Quản Lý Dung Lượng Lưu Trữ Trên Edge (Snapshot Retention)

Để đảm bảo thiết bị phần cứng Edge (Mini PC, Jetson) không bị tràn bộ nhớ:
- **Rolling Buffer Policy**: Giới hạn tối đa **500 snapshots** gần nhất hoặc dung lượng tối đa **1 GB**.
- Khi vượt ngưỡng dung lượng, hệ thống tự động xóa snapshot cũ nhất theo thứ tự FIFO (First In First Out), nhưng **vẫn giữ lại toàn bộ metadata event trong cơ sở dữ liệu**.
