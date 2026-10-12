# Functional & Non-Functional Requirements

# 1. Functional Requirements

## FR-01 Camera input

Hệ thống phải hỗ trợ webcam/camera local.

## FR-02 Video file input

Hệ thống nên hỗ trợ video file để test offline.

## FR-03 Face detection

Phải xác định được có/không có khuôn mặt tài xế.

## FR-04 Eye state

Phải cung cấp tín hiệu trạng thái mắt.

## FR-05 Yawn detection

Phải cung cấp tín hiệu ngáp dựa trên mouth geometry + temporal logic.

## FR-06 Head pose

Phải ước lượng hướng đầu.

## FR-07 Phone detection

Phải phát hiện điện thoại bằng object detector.

## FR-08 Temporal analysis

Phải theo dõi duration của các signal.

## FR-09 Risk calculation

Phải tạo risk score 0–100.

## FR-10 Risk classification

Phải có:

- NORMAL.
- WARNING.
- DANGER.

## FR-11 Alert

Phải tạo cảnh báo khi đủ điều kiện.

## FR-12 Event logging

Phải lưu event vào database.

## FR-13 Realtime status

Frontend phải nhận trạng thái realtime.

## FR-14 Configuration

Cho phép chỉnh threshold.

## FR-15 Session

Một phiên lái xe phải có:

- Start time.
- End time.
- Event count.
- Summary.

---

# 2. Non-Functional Requirements

## NFR-01 Performance

Mục tiêu phát triển:

- >= 20 FPS.
- Pipeline latency < 100 ms nếu phần cứng cho phép.

## NFR-02 Reliability

Một exception ở detector không được làm backend crash toàn bộ nếu có thể recover.

## NFR-03 Offline capability

Critical detection phải chạy offline.

## NFR-04 Privacy

Không bắt buộc upload camera lên cloud.

## NFR-05 Modularity

Các module eye/head/phone phải có thể thay thế độc lập.

## NFR-06 Testability

Temporal/risk logic phải test được mà không cần camera thật.

## NFR-07 Explainability

Mỗi event phải lưu reason.

## NFR-08 Configurability

Không hard-code threshold rải rác trong code.

## NFR-09 Observability

Phải theo dõi:

- FPS.
- Latency.
- Error count.
- Event count.

## NFR-10 Safety limitation

Hệ thống phải được mô tả là driver-assistance prototype, không phải hệ thống an toàn được chứng nhận.
