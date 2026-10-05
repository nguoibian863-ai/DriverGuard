Nhiệm vụ AI-001: sửa logic phát hiện trong ai/runtime/pipeline.py theo kết quả phiên thử người thật (docs/EXPERIMENT_LOG.md mục 11, đọc kỹ). Bạn được chạy lệnh: `.venv/Scripts/python.exe -m pytest ai -q`. Chỉ được sửa: ai/runtime/pipeline.py, ai/runtime/thresholds.py, ai/config/thresholds.yaml, ai/tests/test_pipeline.py (thêm test). Không sửa file khác, không thêm dependency.

Việc cần làm:
1. Ngưỡng ngáp: `mar_threshold` 0,50 -> 0,40 (yaml và giá trị mặc định trong thresholds.py). Cập nhật comment trong yaml: "0.50 -> 0.40 theo thí nghiệm 5".
2. Ngưỡng nhắm mắt: trong `DriverPipeline.ear_threshold`, đổi hệ số 0,7 -> 0,55 và kẹp [0,10; 0,20] (trước là 0,10–0,25). Ngưỡng dự phòng khi chưa hiệu chuẩn `ear_threshold` 0,20 -> 0,15 (yaml và mặc định). Cập nhật docstring cho đúng. Điều chỉnh test hiện có `test_ear_threshold_personalised_to_small_eyes` cho khớp công thức mới (kiểm tra trực tiếp giá trị ngưỡng tính từ baseline, không dựa số cứng sai).
3. Giảm báo giả buồn ngủ: tín hiệu `DROWSINESS_ACUTE`, tích luỹ thời lượng nhắm mắt (`eye_buffer`, `eyes_closed_s`) và mẫu PERCLOS KHÔNG được tính là "nhắm mắt" khi: (a) đã hiệu chuẩn và `rel_pitch > th.pitch_threshold` (đang cúi đầu: đã có sự kiện LOOKING_DOWN), hoặc (b) `mar > th.mar_threshold` (đang ngáp: mắt nheo khi ngáp, đã có tín hiệu ngáp). Cách làm gợi ý: tính `eye_closed_now = ear < self.ear_threshold and not suppress`, và khi suppress thì đẩy giá trị EAR "mở" giả (hoặc reset `eye_buffer`) để không tích luỹ.
4. Mất mặt khi quay đầu lớn: nhớ `last_face_time` và `last_rel_yaw`. Nếu KHÔNG thấy mặt, `now - last_face_time <= 3.0` và `abs(last_rel_yaw) >= 0.8 * th.yaw_threshold` (và đã hiệu chuẩn) thì tín hiệu `LOOKING_AWAY` = True (tiếp tục đếm FSM), và tín hiệu `DRIVER_ABSENCE` = False trong khoảng đó. Sau 3 giây kể từ lần cuối thấy mặt thì quay về logic cũ (DRIVER_ABSENCE).
5. Test mới trong ai/tests/test_pipeline.py (dùng hàm trợ giúp `face`, `run`, `calibrated_pipe` đang có; nếu cần baseline EAR khác thì tạo helper):
   - Cười/nheo mắt: baseline EAR 0,28 (ngưỡng ~0,154), rồi EAR 0,17 trong 3 giây -> KHÔNG có DROWSINESS_ACUTE.
   - Nhắm mắt thật: EAR 0,10 trong 3 giây -> có DROWSINESS_ACUTE.
   - Cúi đầu + EAR thấp: pitch tương đối > 25, EAR 0,10 trong 3 giây -> có LOOKING_DOWN, KHÔNG có DROWSINESS_ACUTE.
   - Ngáp: MAR 0,45 trong 3 giây, EAR 0,12 -> `yawning` True ở cuối, KHÔNG có DROWSINESS_ACUTE.
   - Mất mặt khi quay đầu lớn: thấy mặt với yaw tương đối 45 trong 1 giây rồi mặt mất (None) trong 3 giây -> có LOOKING_AWAY, và trong giai đoạn mất mặt đó KHÔNG có DRIVER_ABSENCE; sau đó mất mặt thêm > 3 giây thì có DRIVER_ABSENCE.
6. Tất cả test cũ trong `ai/` vẫn phải pass (sửa test cũ chỉ khi cần vì đổi công thức/ngưỡng, và nêu rõ trong báo cáo).

Báo cáo ngắn: file đã sửa, kết quả `pytest ai -q`, điểm chưa chắc.
