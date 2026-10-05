# System Architecture

## 1. Kiến trúc tổng thể (Dual-Process & Decoupled-Rate Pipeline)

Hệ thống DriverGuard được thiết kế theo kiến trúc **đa tiến trình (Dual-Process)** nhằm giải phóng hoàn toàn ASGI Event Loop của FastAPI khỏi các phép tính nặng của OpenCV/PyTorch/MediaPipe, đồng thời áp dụng cơ chế **Decoupled-Rate Inference** để tối ưu hóa FPS trên phần cứng Edge:

```text
CAMERA (30 FPS)
     │
     ▼
Latest Frame Buffer (Shared Memory)
     │
     ├──────────────► Face / Landmark Worker (Process A)
     │                     20–30 FPS
     │                         │
     │                         ├── EAR (Mắt)
     │                         ├── MAR (Miệng)
     │                         └── Relative Head Pose (Calibration)
     │
     └──────────────► Phone Detector (Process A)
                           3–5 FPS (ROI-based)
                              │
                              ▼
                    Temporal State Engine (FSM)
                              │
                              ▼
                         Risk Engine
                   (Acute Risk & Chronic Risk + Decay)
                              │
                              ▼
                         Event / Telemetry Queue (multiprocessing.Queue)
                              │
                              ▼
                         FastAPI Server (Process B)
                         │     │
                         │     └── WebSocket telemetry (/ws/status)
                         │
                         └── MJPEG video (/api/v1/video/stream)
                              │
                              ▼
                         Next.js Dashboard
```

---

# 2. Chi tiết các Layer & Cơ chế truyền thông liên tiến trình (IPC)

## 2.1 Process A: Camera & AI Runtime Layer
Trách nhiệm xử lý thu nhận khung hình và suy luận thị giác máy tính:
- **Frame Capture & Buffer**: Đọc luồng video từ webcam/camera ở tần số 30 FPS, lưu vào vùng nhớ đệm khung hình mới nhất (**Latest Frame Buffer / Shared Memory**) với cơ chế zero-copy.
- **Face / Landmark Worker (20–30 FPS)**: Sử dụng MediaPipe Face Mesh trích xuất các điểm mốc hình học mắt (EAR), miệng (MAR) và tư thế đầu (Head Pose).
- **Phone Detector (3–5 FPS)**: Sử dụng YOLO Nano chạy không đồng bộ ở tần suất thấp trên vùng quan tâm (ROI) thay vì toàn bộ khung hình, tiết kiệm tối đa tài nguyên CPU/GPU.
- **Temporal State Engine**: Áp dụng Finite State Machine (FSM: `IDLE -> CANDIDATE -> ACTIVE -> COOLDOWN -> IDLE`) để xác nhận hành vi theo chuỗi thời gian, loại bỏ cảnh báo giả đơn khung hình.
- **Risk Engine**: Đánh giá song song **Nguy cơ cấp tính (Acute)** và **Nguy cơ tích lũy (Chronic)**, áp dụng hàm suy hao (Exponential Decay) khi hành vi kết thúc.

## 2.2 Cơ chế IPC (Inter-Process Communication)
Để đảm bảo FastAPI và giao diện Web luôn mượt mà và không bị latency jitter do tác vụ tính toán AI:
- **multiprocessing.Queue**: Chỉ dùng để đẩy các bản tin JSON telemetry và event nhẹ (vài KB), ví dụ:
  ```json
  {
    "ear": 0.21,
    "mar": 0.34,
    "relative_yaw": 18.2,
    "risk": 42,
    "event": "LOOKING_AWAY"
  }
  ```
- **Shared Memory / Latest Frame Buffer**: Dùng riêng cho truyền khung hình camera sang tiến trình Web Server khi có client kết nối xem video. **Tuyệt đối không gửi frame ảnh thô qua multiprocessing.Queue** để tránh nghẽn I/O và memory copy liên tục.

## 2.3 Process B: FastAPI Backend & Web Layer
- **WebSocket Broadcast**: Tiếp nhận telemetry từ IPC Queue và truyền trực tiếp xuống Next.js Dashboard theo thời gian thực qua `/ws/status`.
- **MJPEG Video Streaming**: Cung cấp endpoint `GET /api/v1/video/stream` (`multipart/x-mixed-replace`) đọc từ Latest Frame Buffer để hiển thị khung hình camera kèm landmark overlay trực tiếp trên trình duyệt.
- **Storage & Event Logger**: Ghi nhận các phiên lái (Session) và sự kiện nguy hiểm (Event) vào SQLite nội bộ kèm chính sách Snapshot Retention hạn chế dung lượng lưu trữ.

## 2.4 Presentation Layer: Next.js Dashboard
- Hiển thị trực tiếp luồng video camera MJPEG.
- Render đồ thị đo lường rủi ro (Risk Meter), điểm EAR/MAR, góc đầu tương đối, tần số FPS và cảnh báo trực quan.
- Gửi các lệnh điều khiển: Bắt đầu/kết thúc session, kích hoạt hiệu chuẩn tư thế (Calibrate), tắt tạm thời âm thanh cảnh báo (Mute Alert).
