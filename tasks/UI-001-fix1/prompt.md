Tự viết code TRỰC TIẾP bằng công cụ ghi file. KHÔNG giao subagent, KHÔNG chạy lệnh shell. Khi ghi xong, trả lời theo định dạng ở cuối (bắt đầu bằng "## OUTPUT_START", kết thúc bằng "## OUTPUT_END").

Đây là vòng sửa lỗi (fix 1/3) cho task UI-001 sau khi Claude review. CHỈ sửa đúng các lỗi dưới đây, không thiết kế lại gì khác.

Lỗi 1 — eslint (react-hooks) ở apps/web/components/driver/status-screen.tsx:
- `react-hooks/refs`: đọc `dangerSinceMsRef.current` trong lúc render (khi gọi `alertStage({... dangerSinceMs: dangerSinceMsRef.current ...})`).
- Nguyên nhân gốc: dùng ref để lưu mốc bắt đầu DANGER rồi đọc nó khi render.
- Yêu cầu sửa: không đọc ref trong render và không gọi setState đồng bộ trong thân effect (`react-hooks/set-state-in-effect`). Gợi ý: giữ mốc DANGER và mức hiện tại trong ref, được cập nhật trong effect; tính `stage` bên trong callback của `setInterval` 500 ms (callback được phép đọc ref) rồi `setStage(...)`; truyền `stage` (state) vào `useAlertSound` và vào phần hiển thị cần leo thang. Độ trễ tối đa 500 ms của stage là chấp nhận được. Các thuộc tính mới nhất (level, muted, connected, calibrated) cũng lấy qua ref cập nhật trong effect.

Lỗi 2 — eslint `react-hooks/set-state-in-effect` ở apps/web/components/driver/calibration-ring.tsx (gọi setProgress/setSecondsRemaining đồng bộ trong thân effect để đặt lại).
- Yêu cầu sửa: để component chỉ được MOUNT khi điều kiện đếm đúng (`connected && !calibrated && faceDetected`) — cha (status-screen) render `<CalibrationRing />` có điều kiện, nhờ đó mỗi lần điều kiện đúng là một lần mount mới, bắt đầu từ 0 mà không cần "đặt lại" trong effect. Trong component, chỉ gọi setState bên trong callback của setInterval. Bỏ các prop `connected`, `calibrated`, `faceDetected` nếu không còn cần.

Lỗi 3 — LỖI LOGIC NGHIÊM TRỌNG ở calibration-ring.tsx: sau 4 giây component gọi `postCalibrate()`. Backend ĐÃ TỰ hiệu chuẩn khi thấy mặt lần đầu, và lệnh calibrate làm backend ĐẶT LẠI hiệu chuẩn, nên `calibrated` quay về false và vòng đếm chạy lại mãi mãi.
- Yêu cầu sửa: vòng đếm chỉ để HIỂN THỊ tiến độ, TUYỆT ĐỐI không gọi `postCalibrate()` (xóa import nếu không dùng). Khi đếm xong mà backend chưa báo `calibrated` thì giữ vòng ở 100% với chữ "Đang hoàn tất…". Nút "Hiệu chuẩn lại" ở status-screen vẫn gọi postCalibrate() như cũ (đó là hành động do người dùng chủ động).

Do Not Modify: mọi file ngoài apps/web/components/driver/status-screen.tsx và apps/web/components/driver/calibration-ring.tsx (nếu cần thay đổi lib/useAlertSound.ts thì nêu rõ lý do trong báo cáo thay vì tự sửa).
Out Of Scope: mọi thay đổi giao diện, kiểu dáng, luồng khác.

Tiêu chí: `npx eslint components/driver` không còn lỗi; hành vi hiển thị giữ nguyên; không gọi postCalibrate() tự động.

## OUTPUT_START
1. Các file đã sửa
2. Mô tả ngắn cách sửa từng lỗi
3. Điểm chưa chắc
## OUTPUT_END
