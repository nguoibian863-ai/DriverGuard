1. Danh sách file đã tạo/sửa
- [apps/web/app/camera/camera.css](file:///D:/D%E1%BB%B1%20%C3%81n%20C%C3%A1%20Nh%C3%A2n/DriverGuard_Documentation/apps/web/app/camera/camera.css) (tạo mới)
- [apps/web/components/camera/live-view.tsx](file:///D:/D%E1%BB%B1%20%C3%81n%20C%C3%A1%20Nh%C3%A2n/DriverGuard_Documentation/apps/web/components/camera/live-view.tsx) (tạo mới)
- [apps/web/app/camera/page.tsx](file:///D:/D%E1%BB%B1%20%C3%81n%20C%C3%A1%20Nh%C3%A2n/DriverGuard_Documentation/apps/web/app/camera/page.tsx) (tạo mới)
- [apps/web/app/monitor/page.tsx](file:///D:/D%E1%BB%B1%20%C3%81n%20C%C3%A1%20Nh%C3%A2n/DriverGuard_Documentation/apps/web/app/monitor/page.tsx) (thêm nút Camera vào header điều hướng)
- [apps/web/components/driver/status-screen.tsx](file:///D:/D%E1%BB%B1%20%C3%81n%20C%C3%A1%20Nh%C3%A2n/DriverGuard_Documentation/apps/web/components/driver/status-screen.tsx) (thêm liên kết Camera cạnh Giám sát ở footer)
- [apps/web/components/driver/start-gate.tsx](file:///D:/D%E1%BB%B1%20%C3%81n%20C%C3%A1%20Nh%C3%A2n/DriverGuard_Documentation/apps/web/components/driver/start-gate.tsx) (thêm liên kết Camera cạnh Giám sát ở footer)
- [MEMORY.md](file:///D:/D%E1%BB%B1%20%C3%81n%20C%C3%A1%20Nh%C3%A2n/DriverGuard_Documentation/MEMORY.md) (cập nhật tiến độ task UI-005)

2. Giải thích ngắn
- Thêm route `/camera` với giao diện phẳng chuẩn HMI/docs/ui-design-spec.md: khung video 4:3 nền đen, bo 6 px, viền 1 px token `--border`.
- Xử lý các lớp phủ video độc quyền theo mức ưu tiên: chưa kết nối backend, camera bận (`camera_unavailable`), và đang chờ khung hình đầu tiên qua `onLoad` của `<img>`.
- Khi có hình mà mất mặt (`!telemetry.face_detected`), hiển thị thông báo "Không thấy khuôn mặt" bên dưới khung video thay vì đè lên hình ảnh.
- Tích hợp tính năng ngắt stream (gán `src = undefined`) khi tab ẩn (`visibilitychange`) và nạp lại luồng kèm query `&t=<timestamp>` khi tab hiển thị lại.
- Bổ sung nút "Toàn màn hình" gọi Fullscreen API trên khung video (tự ẩn nếu trình duyệt không hỗ trợ, thoát bằng Esc hoặc nút toggle).
- Hàng chỉ số dưới video thể hiện mức rủi ro (badge vuông kèm SVG), FPS và độ trễ dùng `tabular-nums`; liên kết điều hướng được chèn đồng bộ vào `/monitor`, `StatusScreen`, và `StartGate`.

3. Rủi ro / điểm chưa chắc
- Trình duyệt Safari/iOS có thể hạn chế Fullscreen API trên thẻ `<div>` không phải `<video>` (mã đã phòng ngừa bằng kiểm tra hỗ trợ và ẩn nút khi không khả dụng).
- Sự kiện `onLoad` của ảnh luồng MJPEG phụ thuộc vào việc trình duyệt nhận boundary frame đầu tiên; nếu backend stream ngắt giữa chừng mà WebSocket vẫn giữ kết nối, cần chờ bản tin telemetry tiếp theo để đồng bộ trạng thái.
