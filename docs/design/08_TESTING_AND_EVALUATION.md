# Testing & Evaluation

# 1. Mục tiêu đánh giá

Không chỉ kiểm tra model có chạy hay không, mà phải đánh giá toàn diện:
- **Detection quality**: Chất lượng mô hình nhận diện tĩnh.
- **Temporal event quality**: Độ chính xác theo chuỗi thời gian (FSM confirmation).
- **Realtime performance**: Tần số FPS và độ trễ trên phần cứng Edge.
- **Stability**: Khả năng phục hồi khi mất frame, camera rung lắc hoặc tài xế đeo kính/khẩu trang.

---

# 2. Benchmark Datasets Chuẩn Ngành

Để định lượng chính xác Precision, Recall và F1-Score thay vì chỉ dùng dữ liệu định tính:

1. **NTHU Driver Drowsiness Detection Dataset (NTHU-DDD)**:
   - Đánh giá khả năng phát hiện nhắm mắt kéo dài (EAR) và ngủ gật.
   - Kiểm thử trong các kịch bản khó: Ban ngày, ban đêm (ánh sáng yếu), có/không đeo kính.
2. **YawDD (Yawning Detection Dataset)**:
   - Bộ video chuyên biệt về biểu cảm miệng và hành vi ngáp trong khoang lái xe.
   - Dùng để cân chỉnh ngưỡng MAR và phân biệt giữa nói chuyện vs ngáp thật.
3. **State Farm Distracted Driver Detection Dataset**:
   - Đánh giá khả năng phát hiện hành vi dùng điện thoại (`PHONE_USAGE`) và quay đầu (`LOOKING_AWAY`).
4. **Internal Recorded Driving Scenarios**:
   - Bộ 10–15 video kịch bản nội bộ (Edge testing videos) gắn camera ở các góc lệch thực tế trên ô tô để kiểm tra tính năng **Neutral Pose Calibration**.

---

# 3. Temporal Event Metrics

Đây là thước đo quan trọng nhất của hệ thống DriverGuard:

Ví dụ Ground Truth:
```text
00:14.0 → 00:16.2 looking away (2.2 s)
```
Hệ thống dự đoán:
```text
00:14.3 → 00:16.4 looking away (2.1 s)
```

Chỉ số đo lường bắt buộc:
- **Event Precision & Recall**: Tỷ lệ sự kiện phát hiện đúng trên tổng số sự kiện thực tế.
- **Detection Delay**: Độ trễ từ khi hành vi bắt đầu đến khi phát ra cảnh báo (mục tiêu: $\le 300\text{ms}$ sau khi vượt ngưỡng duration).
- **False Alarms / Minute**: Tần suất báo động giả trong điều kiện lái xe bình thường (mục tiêu: $< 0.1$ lần/phút).
- **Missed Events**: Tỷ lệ bỏ sót các hành vi buồn ngủ cấp tính (mục tiêu: $0\%$ với sự kiện nhắm mắt $> 2.0\text{s}$).

---

# 4. Runtime Metrics (Hiệu năng hệ thống)

Ghi nhận liên tục theo chu kỳ:
```text
Camera Capture FPS  : >= 30 FPS
Face Pipeline FPS   : 20–30 FPS
Phone Pipeline FPS  : 3–5 FPS
Mean Pipeline Latency: < 50 ms
P95 Latency         : < 100 ms
CPU Usage           : < 60%
RAM Usage           : < 1.5 GB
```

---

# 5. Unit Tests & Integration Tests

## Unit Tests
- `test_ear_calculation`: Kiểm tra tính toán EAR với các landmark mắt chuẩn.
- `test_mar_calculation`: Kiểm tra tính toán MAR với các landmark miệng.
- `test_neutral_pose_calibration`: Kiểm tra thuật toán tính median và trừ góc tương đối ($relative\_yaw, relative\_pitch$).
- `test_phone_roi_filter`: Kiểm tra lọc điện thoại theo khoảng cách hand/face ROI.
- `test_state_machine_transitions`: Kiểm tra chuyển trạng thái `IDLE -> CANDIDATE -> ACTIVE -> COOLDOWN`.
- `test_risk_decay`: Kiểm tra hàm phân rã EMA không bị rớt điểm đột ngột về 0.

## Integration Tests
- Chạy video offline từ dataset qua pipeline và so sánh danh sách event sinh ra với ground truth annotations.

---

# 6. Test Scenarios (12 Kịch Bản Thực Tế)

1. Tài xế lái xe bình thường.
2. Chớp mắt tự nhiên (không kích hoạt cảnh báo).
3. Nhắm mắt kéo dài > 1.8s (kích hoạt DANGER tức thì).
4. Ngáp nhiều lần (kích hoạt Chronic Fatigue).
5. Quay đầu sang trái (nhìn gương chiếu hậu/cửa sổ).
6. Quay đầu sang phải.
7. Cúi đầu nhìn xuống (nhìn bảng điều khiển/điện thoại).
8. Dùng điện thoại trên tay (PHONE_USAGE).
9. Điện thoại gắn cố định trên giá taplo (PHONE_VISIBLE, không báo động).
10. Tài xế rời khỏi vị trí lái / khuất mặt (DRIVER_ABSENCE).
11. Điều kiện ánh sáng yếu / ngược sáng.
12. Tài xế đeo kính cận / kính râm.
