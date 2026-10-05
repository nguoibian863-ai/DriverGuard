1. Các file đã sửa:
- [apps/web/components/driver/status-screen.tsx](file:///D:/D%E1%BB%B1%20%C3%81n%20C%C3%A1%20Nh%C3%A2n/DriverGuard_Documentation/apps/web/components/driver/status-screen.tsx)
- [apps/web/components/driver/calibration-ring.tsx](file:///D:/D%E1%BB%B1%20%C3%81n%20C%C3%A1%20Nh%C3%A2n/DriverGuard_Documentation/apps/web/components/driver/calibration-ring.tsx)

2. Mô tả ngắn cách sửa từng lỗi:
- **Lỗi 1 (`react-hooks/refs` & `react-hooks/set-state-in-effect` ở [`status-screen.tsx`](file:///D:/D%E1%BB%B1%20%C3%81n%20C%C3%A1%20Nh%C3%A2n/DriverGuard_Documentation/apps/web/components/driver/status-screen.tsx)):**
  + Chuyển việc cập nhật mốc DANGER (`dangerSinceMsRef`) và các giá trị telemetry mới nhất (`level`, `muted`, `connected`, `calibrated` qua `stateRef`) vào trong `useEffect`.
  + Loại bỏ việc đọc `dangerSinceMsRef.current` trong lúc render. Đưa logic tính `alertStage` vào bên trong callback của `setInterval` 500 ms (nơi được phép đọc ref mà không vi phạm quy tắc render) và lưu vào state `stage`.
  + Loại bỏ state `nowMs` không còn cần thiết; truyền state `stage` vào [`useAlertSound`](file:///D:/D%E1%BB%B1%20%C3%81n%20C%C3%A1%20Nh%C3%A2n/DriverGuard_Documentation/apps/web/lib/useAlertSound.ts).

- **Lỗi 2 (`react-hooks/set-state-in-effect` ở [`calibration-ring.tsx`](file:///D:/D%E1%BB%B1%20%C3%81n%20C%C3%A1%20Nh%C3%A2n/DriverGuard_Documentation/apps/web/components/driver/calibration-ring.tsx)):**
  + Tại component cha [`StatusScreen`](file:///D:/D%E1%BB%B1%20%C3%81n%20C%C3%A1%20Nh%C3%A2n/DriverGuard_Documentation/apps/web/components/driver/status-screen.tsx), render [`<CalibrationRing />`](file:///D:/D%E1%BB%B1%20%C3%81n%20C%C3%A1%20Nh%C3%A2n/DriverGuard_Documentation/apps/web/components/driver/calibration-ring.tsx) có điều kiện theo biểu thức: `connected && !isCalibrated && (telemetry?.face_detected ?? false)`.
  + Nhờ cơ chế mount có điều kiện, mỗi khi điều kiện thỏa mãn thì component được mount mới với `progress = 0` và đếm từ đầu; khi mất kết nối, đã hiệu chuẩn hoặc mất dấu khuôn mặt thì component tự động unmount.
  + Loại bỏ hoàn toàn logic gọi `setProgress(0)` / `setSecondsRemaining(4)` đồng bộ trong thân `useEffect`. Trong [`CalibrationRing`](file:///D:/D%E1%BB%B1%20%C3%81n%20C%C3%A1%20Nh%C3%A2n/DriverGuard_Documentation/apps/web/components/driver/calibration-ring.tsx), `setState` chỉ được gọi bên trong callback của `setInterval`.
  + Bỏ các prop `connected`, `calibrated`, `faceDetected` không còn cần dùng ở [`CalibrationRing`](file:///D:/D%E1%BB%B1%20%C3%81n%20C%C3%A1%20Nh%C3%A2n/DriverGuard_Documentation/apps/web/components/driver/calibration-ring.tsx).

- **Lỗi 3 (Lỗi logic tự gọi `postCalibrate()` ở [`calibration-ring.tsx`](file:///D:/D%E1%BB%B1%20%C3%81n%20C%C3%A1%20Nh%C3%A2n/DriverGuard_Documentation/apps/web/components/driver/calibration-ring.tsx)):**
  + Xóa bỏ import và lệnh gọi `postCalibrate()` trong [`calibration-ring.tsx`](file:///D:/D%E1%BB%B1%20%C3%81n%20C%C3%A1%20Nh%C3%A2n/DriverGuard_Documentation/apps/web/components/driver/calibration-ring.tsx).
  + Khi hết 4 giây (`elapsed >= TOTAL_MS`), xóa timer và giữ tiến độ vòng ở mức 100% cùng nội dung `"Đang hoàn tất…"` cho đến khi backend cập nhật `calibrated: true` (khi đó cha sẽ unmount overlay).
  + Nút "Hiệu chuẩn lại" ở [`status-screen.tsx`](file:///D:/D%E1%BB%B1%20%C3%81n%20C%C3%A1%20Nh%C3%A2n/DriverGuard_Documentation/apps/web/components/driver/status-screen.tsx) vẫn giữ nguyên lệnh gọi `postCalibrate()` do người dùng chủ động kích hoạt.

3. Điểm chưa chắc:
- Do tuân thủ yêu cầu không chạy lệnh shell trong lượt này, việc thực thi lệnh `npx eslint components/driver` chưa được kiểm tra trực tiếp qua shell; tuy nhiên cấu trúc mã nguồn đã được rà soát kỹ lưỡng theo các quy tắc `react-hooks/refs`, `react-hooks/set-state-in-effect` và `react-hooks/exhaustive-deps`.
- Thời gian hiển thị trạng thái 100% ("Đang hoàn tất…") sẽ phụ thuộc vào độ trễ vòng lặp telemetry từ AI backend cho đến khi cờ `calibrated: true` được phát qua WebSocket.
