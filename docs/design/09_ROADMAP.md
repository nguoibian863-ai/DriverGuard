# Development Roadmap

Kế hoạch phát triển 10 giai đoạn được tái cơ cấu để dựng sớm khung Process/IPC, hạn chế triệt để rủi ro xung đột tích hợp về sau:

---

## Phase 0 — Project & IPC Skeleton

### Mục tiêu
Dựng toàn bộ cấu trúc khung xương monorepo và cơ chế đa tiến trình (Dual-Process):
- Khung `ai/` package và Camera capture loop.
- Khung `apps/backend/` (FastAPI) và `apps/web/` (Next.js).
- Kiểm thử cơ chế **multiprocessing.Queue** (gửi telemetry giả lập từ AI Worker sang FastAPI) và Shared Memory buffer.

---

## Phase 1 — Camera + Frame Buffer + WebSocket Test

### Deliverables
- Module đọc Camera 30 FPS bằng OpenCV.
- Vùng nhớ đệm **Latest Frame Buffer** (Shared Memory).
- AI Worker process gửi nhịp tim/FPS sang FastAPI qua IPC Queue.
- Endpoint `/ws/status` phát sóng telemetry kết nối thành công tới Frontend.

---

## Phase 2 — Face Landmark + EAR + Calibration

### Deliverables
- Tích hợp MediaPipe Face Mesh (468/478 landmarks).
- Tính toán chỉ số EAR cho mắt.
- Module **Neutral Pose Calibration**: Cửa sổ 3–5 giây tính Median $(\text{yaw}_0, \text{pitch}_0)$ tại thời điểm bắt đầu phiên lái.

---

## Phase 3 — Drowsiness + Temporal FSM

### Deliverables
- Tính toán chỉ số MAR cho miệng (phát hiện ngáp).
- Xây dựng Finite State Machine (`IDLE -> CANDIDATE -> ACTIVE -> COOLDOWN -> IDLE`).
- Cơ chế Temporal Smoothing: Xác nhận sự kiện nhắm mắt/ngáp theo thời gian thực tế thay vì khung hình đơn lẻ.

---

## Phase 4 — Head Pose + Distraction

### Deliverables
- Ước lượng góc xoay đầu: $\text{relative\_yaw} = \text{yaw} - \text{yaw}_0$ và $\text{relative\_pitch} = \text{pitch} - \text{pitch}_0$.
- Sự kiện `LOOKING_AWAY` khi quay mặt trái/phải quá ngưỡng.
- Sự kiện `LOOKING_DOWN` khi cúi đầu quá lâu.

---

## Phase 5 — YOLO Phone + Decoupled Inference Rate

### Deliverables
- Tích hợp Ultralytics YOLO Nano chạy trên luồng không đồng bộ với tần suất **3–5 FPS**.
- Bộ lọc ROI không gian: Phân biệt `PHONE_VISIBLE` (gắn trên giá taplo) và `PHONE_USAGE` (cầm trên tay gần vùng mặt/ngực).
- Đảm bảo tần số Face Pipeline vẫn duy trì ổn định $\ge 20–30\text{ FPS}$.

---

## Phase 6 — Dual Risk Engine (Acute & Chronic + Decay)

### Deliverables
- **Acute Risk Subsystem**: Kích hoạt thẳng DANGER khi nhắm mắt $> 1.8\text{s}$ hoặc dùng điện thoại liên tục.
- **Chronic Risk Subsystem**: Tính điểm mệt mỏi tích lũy (PERCLOS và ngáp lặp lại nhiều lần).
- **Exponential Decay Function**: Điểm rủi ro hạ dần theo thời gian ($80 \to 72 \to 64 \dots$) khi kết thúc hành vi nguy hiểm.

---

## Phase 7 — Dashboard + Video Stream + Events

### Deliverables
- Endpoint `GET /api/v1/video/stream` (MJPEG streaming trực tiếp lên giao diện).
- Giao diện Next.js Dashboard:
  - Video feed hiển thị trực tiếp.
  - Risk Meter, đồ thị EAR/MAR, còi/cảnh báo trực quan.
  - Nút bấm Calibrate và Mute Alert.
  - Bảng sự kiện lịch sử (lưu vào SQLite kèm rolling retention 500 ảnh).

---

## Phase 8 — Dataset Evaluation

### Deliverables
- Chạy kiểm thử offline tự động trên các bộ benchmark:
  - **NTHU-DDD** (buồn ngủ/nhắm mắt).
  - **YawDD** (ngáp).
  - **State Farm** (dùng điện thoại/mất tập trung).
- Đo lường và lập báo cáo: F1-Score, Detection Delay, False Alarms/min.

---

## Phase 9 — ONNX Runtime & Edge Optimization

### Deliverables
- Chuyển đổi mô hình YOLO và Landmark sang format **ONNX Runtime**.
- Tối ưu hóa kích thước model và benchmark trên phần cứng mục tiêu (Mini PC / NVIDIA Jetson).
- Đóng gói Docker Compose chạy local-first hoàn chỉnh.
