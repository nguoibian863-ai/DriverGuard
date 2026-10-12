# Actors & User Requirements

## 1. Actors

### 1.1 Driver

Người đang điều khiển xe và được hệ thống giám sát.

**Mục tiêu**

- Được cảnh báo kịp thời khi có dấu hiệu buồn ngủ hoặc mất tập trung.
- Không bị làm phiền bởi quá nhiều cảnh báo sai.
- Có thể xem lại các sự kiện nguy hiểm sau hành trình.

### 1.2 Vehicle / Edge Device

Thiết bị chạy DriverGuard trên xe.

Ví dụ:

- Laptop.
- Mini PC.
- NVIDIA Jetson.
- Thiết bị edge tương đương.

**Trách nhiệm**

- Nhận video camera.
- Chạy inference.
- Phân tích temporal.
- Sinh cảnh báo.
- Lưu event.

### 1.3 Safety Supervisor / Fleet Manager

Người theo dõi trạng thái an toàn hoặc xem báo cáo sau hành trình.

**Mục tiêu**

- Xem danh sách sự kiện.
- Xem mức độ nguy hiểm.
- Xem thời gian xảy ra.
- Xem tổng hợp hành trình.
- Phân tích tần suất mất tập trung / buồn ngủ.

### 1.4 System Administrator

Người cấu hình và vận hành hệ thống.

**Mục tiêu**

- Cấu hình camera.
- Cấu hình threshold.
- Bật/tắt module.
- Kiểm tra trạng thái model.
- Kiểm tra log.

### 1.5 AI/ML Engineer

Người phát triển và đánh giá model.

**Mục tiêu**

- Thử nghiệm model.
- Benchmark accuracy.
- Benchmark FPS/latency.
- Fine-tune model nếu cần.
- Export ONNX/TensorRT.

---

# 2. User Requirements

## UR-01 — Realtime monitoring

Hệ thống phải có khả năng đọc luồng camera và xử lý liên tục theo thời gian thực.

## UR-02 — Drowsiness detection

Hệ thống phải phát hiện dấu hiệu buồn ngủ dựa trên chuỗi thời gian thay vì một frame đơn.

Ví dụ:

- Nhắm mắt kéo dài.
- PERCLOS cao.
- Ngáp liên tục.

## UR-03 — Distraction detection

Hệ thống phải phát hiện tài xế nhìn khỏi hướng lái hoặc quay/cúi đầu quá lâu.

## UR-04 — Phone usage detection

Hệ thống phải cảnh báo khi phát hiện điện thoại trong vùng liên quan đến tài xế trong một khoảng thời gian đủ dài.

## UR-05 — Driver absence

Hệ thống phải phát hiện trường hợp mất khuôn mặt hoặc không tìm thấy tài xế trong camera.

## UR-06 — Temporal confirmation

Không được đưa ra cảnh báo nguy hiểm chỉ từ một frame bất thường.

Ví dụ:

```text
eyes_closed = true trong 1 frame
→ không cảnh báo

eyes_closed = true liên tục > threshold
→ tạo event
```

## UR-07 — Risk level

Hệ thống phải phân loại tối thiểu ba mức:

- NORMAL
- WARNING
- DANGER

## UR-08 — Alert

Khi đạt mức WARNING hoặc DANGER, hệ thống phải hỗ trợ:

- Cảnh báo âm thanh.
- Cảnh báo trực quan.
- Ghi event.

## UR-09 — Event history

Người dùng phải xem được:

- Loại sự kiện.
- Timestamp.
- Risk score.
- Duration.
- Confidence.
- Snapshot nếu được bật.

## UR-10 — Dashboard

Dashboard phải hiển thị tối thiểu:

- Camera feed.
- Driver status.
- Risk score.
- FPS.
- Latency.
- Event gần nhất.
- Event history.

## UR-11 — Local processing

Các chức năng cảnh báo realtime cốt lõi phải chạy được mà không phụ thuộc LLM hoặc Internet.

## UR-12 — Configurable thresholds

Admin phải chỉnh được các ngưỡng như:

- Eye closure duration.
- Looking-away duration.
- Yawning threshold.
- Phone duration.
- Risk weights.

## UR-13 — Explainability

Mỗi cảnh báo phải có nguyên nhân rõ ràng.

Ví dụ:

```text
DANGER
Reason:
- Eyes closed: 1.8 s
- Looking down: 2.2 s
- Risk score: 78
```

## UR-14 — Privacy

MVP mặc định không cần nhận dạng danh tính.

Video không bắt buộc lưu toàn bộ; ưu tiên chỉ lưu metadata/event.

## UR-15 — Performance

Mục tiêu MVP:

- FPS: >= 20 FPS trên máy phát triển.
- Pipeline latency: cố gắng < 100 ms.
- Không treo UI khi inference.
