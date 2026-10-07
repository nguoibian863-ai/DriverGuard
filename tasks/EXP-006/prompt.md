Nhiệm vụ EXP-006: chuẩn bị Thí nghiệm 6 (phiên thử người thật lần 2, tập kiểm tra độc lập sau khi đã đổi ngưỡng ở AI-001). Đọc docs/EXPERIMENT_LOG.md mục 11 và 12 trước. Bạn được chạy lệnh: `.venv/Scripts/python.exe <script>` và `.venv/Scripts/python.exe -m pytest ai -q`. Chỉ được sửa/tạo: scripts/live_session.py, scripts/score_live_session.py (mới), scripts/replay_live_session.py (chỉ nếu cần nhận tham số đường dẫn). KHÔNG sửa ai/, apps/, docs/ (kể cả docs/experiments/live_session.json — là dữ liệu thí nghiệm 5, tuyệt đối không ghi đè), không thêm dependency.

Việc cần làm:
1. scripts/live_session.py:
   a. Nhận đối số dòng lệnh `--out <đường dẫn>` (mặc định giữ nguyên docs/experiments/live_session.json) và `--label <chuỗi>` (ghi vào JSON kết quả, khoá "label"). Nếu tệp đích đã tồn tại thì dừng và báo lỗi, không ghi đè (trừ khi có cờ `--force`).
   b. Ngay trước khi pha đầu bắt đầu (sau bước đếm ngược 3-2-1, trước khi ghi mốc `baseline`), trang gọi backend để hiệu chuẩn lại: POST http://localhost:8000/api/v1/sessions/calibrate (làm qua một route của server nhỏ ở cổng 8777, ví dụ /calibrate, để tránh CORS), rồi đợi 4 giây "Ngồi thẳng, nhìn thẳng" trước khi vào pha baseline. Ghi mốc thời gian hiệu chuẩn vào JSON ("calibrate_t"). Khắc phục lỗi thiết lập đã ghi ở mục 11.1.
   c. Bổ sung kịch bản (giữ các pha cũ, chèn thêm): lặp lại "look_left" và "look_right" mỗi cái thêm một lần nữa nhưng yêu cầu quay mạnh hơn ("quay sang trái/phải ĐẾN KHI nhìn thấy mép cửa sổ, giữ yên"); thêm pha "phone_near_face" (6 giây): "Đưa điện thoại lên NGANG MẶT như đang nhắn tin, mắt nhìn vào điện thoại". Giữ pha "phone" cũ. Cập nhật câu mô tả "~100 giây" cho đúng tổng thời gian mới.
   d. Ghi thêm vào mỗi bản tin các trường hiện có trong telemetry nếu tồn tại: "phone_roi" hoặc tên tương tự (nếu không có thì bỏ qua, không bịa).
2. scripts/score_live_session.py (mới): đọc tệp JSON phiên thử (đối số `--in`, mặc định docs/experiments/live_session_2.json), chấm điểm TỰ ĐỘNG theo pha dựa trên marks:
   - Với mỗi pha mong đợi: eyes_closed -> sự kiện DROWSINESS_ACUTE hoặc cờ eyes_closed; look_left/look_right (cả lần lặp) -> LOOKING_AWAY; look_down -> LOOKING_DOWN; yawn -> cờ yawning hoặc sự kiện YAWNING; phone, phone_near_face -> PHONE_USAGE hoặc phone_detected.
   - Với pha KHÔNG được báo (blink, talk, smile, rest*, baseline): đếm sự kiện cảnh báo bất kỳ (DROWSINESS_ACUTE, LOOKING_AWAY, LOOKING_DOWN, YAWNING, PHONE_USAGE, DRIVER_ABSENCE) là báo giả; riêng sự kiện nằm trong 2 giây đầu sau mốc đổi pha thì tính là "trễ chuyển pha" và báo riêng, không tính báo giả.
   - Với mỗi pha mong đợi: độ trễ phát hiện (giây từ mốc pha đến lần đầu có cờ/sự kiện), tỉ lệ bản tin có cờ, thấy mặt %.
   - In bảng tiếng Việt có dấu theo pha + tổng: số pha phát hiện đúng / tổng, số báo giả, độ trễ trung vị. Ghi thêm tệp CSV cạnh tệp JSON (cùng tên, đuôi .csv) cho báo cáo. Lưu ý rõ trong đầu ra: đây là chấm theo mốc hướng dẫn, người thử có thể phản ứng sớm/muộn.
   - Kiểm tra bằng cách chạy trên docs/experiments/live_session.json (dữ liệu thí nghiệm 5; không có calibrate_t/label thì xử lý được, các pha lặp/phone_near_face không có thì bỏ qua) và dán kết quả vào báo cáo.
3. Chạy `.venv/Scripts/python.exe -m pytest ai -q` để chắc không hỏng gì (bạn không sửa ai/ nên phải giữ nguyên kết quả: 48 passed).
4. Kiểm tra cú pháp live_session.py bằng `.venv/Scripts/python.exe -m py_compile scripts/live_session.py` (không chạy thật vì cần camera/backend).

Báo cáo ngắn: file đã sửa/tạo, kết quả chấm thử trên dữ liệu thí nghiệm 5, kết quả pytest, điểm chưa chắc.
