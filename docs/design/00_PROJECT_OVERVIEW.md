# DriverGuard — Project Overview

## 1. Tên đề tài

**DEV-02 — DriverGuard: Hệ thống giám sát tài xế (DMS) phát hiện buồn ngủ và mất tập trung on-device**

## 2. Bài toán

DriverGuard sử dụng camera trong khoang lái để giám sát tài xế theo thời gian thực, phát hiện các dấu hiệu rủi ro như:

- Buồn ngủ / nhắm mắt kéo dài.
- Ngáp nhiều.
- Quay đầu hoặc nhìn khỏi hướng lái quá lâu.
- Cúi đầu.
- Sử dụng điện thoại khi lái xe.
- Không phát hiện được khuôn mặt tài xế.
- Chuỗi hành vi bất thường kéo dài theo thời gian.

Hệ thống ưu tiên xử lý **on-device**, giảm phụ thuộc Internet và giảm độ trễ cảnh báo.

## 3. Mục tiêu sản phẩm

Xây dựng một MVP có khả năng:

1. Nhận video từ webcam/camera.
2. Phát hiện khuôn mặt và landmark.
3. Phân tích mắt, miệng và hướng đầu.
4. Phát hiện điện thoại.
5. Phân tích hành vi theo chuỗi thời gian.
6. Tính mức độ rủi ro.
7. Cảnh báo realtime.
8. Ghi log sự kiện.
9. Hiển thị dashboard.
10. Tổng hợp báo cáo hành trình.

## 4. Phạm vi MVP

### In scope

- Driver detection.
- Eye closure.
- Yawning.
- Head pose.
- Looking away.
- Phone usage.
- Driver absence.
- Temporal analysis.
- Risk score.
- Audio/UI alert.
- Event history.
- Dashboard realtime.

### Out of scope ở MVP

- Điều khiển trực tiếp xe.
- Can thiệp phanh/ga/vô lăng.
- Nhận dạng danh tính tài xế.
- Chẩn đoán y tế.
- Full autonomous driving / ADAS.
- Cloud-scale fleet management.
- Huấn luyện foundation model riêng.

## 5. Luồng tổng quát (Decoupled-Rate & Dual-Risk)

```text
Camera (30 FPS)
   ↓
Latest Frame Buffer (Shared Memory)
   ↓
┌─────────────────────────────────┬─────────────────────────────────┐
│ Face / Landmarks (20–30 FPS)    │ Object Detection (3–5 FPS)      │
│ Eyes (EAR) | Mouth (MAR)        │ Phone Detection (Hand/Face ROI) │
│ Relative Head Pose (Calibrated) │                                 │
└────────────────┬────────────────┴────────────────┬────────────────┘
                 ↓                                 ↓
           Temporal State Engine (FSM Smoothing)
                           ↓
                   Dual Risk Engine
              (Acute Bypass & Chronic Decay)
                           ↓
                NORMAL / WARNING / DANGER
                           ↓
     ┌─────────────────────┴─────────────────────┐
     ↓                                           ↓
Telemetry/Events (multiprocessing.Queue)     MJPEG Stream (Shared Memory)
     ↓                                           ↓
FastAPI WebSocket                            FastAPI /video/stream
     └─────────────────────┬─────────────────────┘
                           ↓
                   Next.js Dashboard
```

## 6. Tiêu chí thành công

MVP được coi là hoàn thành khi:

- Camera chạy ổn định realtime.
- Phát hiện được tối thiểu 4 nhóm hành vi chính.
- Không cảnh báo chỉ dựa vào một frame đơn lẻ.
- Có temporal smoothing.
- Có risk score.
- Có event log.
- Có giao diện realtime.
- Đo được Precision, Recall, F1, FPS và latency.
