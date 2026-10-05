Tự viết code TRỰC TIẾP bằng công cụ ghi file. KHÔNG giao subagent, KHÔNG chạy lệnh shell (Claude sẽ chạy lint/build/test). Khi ghi xong, trả lời theo định dạng ở cuối (bắt đầu bằng "## OUTPUT_START", kết thúc bằng "## OUTPUT_END").

Task UI-005: thêm màn hình XEM CAMERA TRỰC TIẾP tại route "/camera" cho dashboard DriverGuard (apps/web, Next.js 16 App Router, React 19, TypeScript, Tailwind 4). ĐỌC KỸ docs/ui-design-spec.md và làm đúng (phẳng, không glow/gradient/pill, token màu bằng biến CSS --bg --surface --border --text --text-muted --accent --ok --warn --danger..., Inter, chữ ngắn, vùng bấm ≥ 44 px, có focus ring). Giữ phong cách nhất quán với app/monitor (xem app/monitor/page.tsx, monitor.css, components/monitor/*).

Dữ liệu sẵn có:
- Luồng video MJPEG: `${API_URL}/api/v1/video/stream?overlay=true` (API_URL từ lib/api.ts). Thẻ <img> hiển thị luồng liên tục.
- Hook `useTelemetry()` (lib/useTelemetry.ts) trả `{ telemetry, connected, history }`; kiểu Telemetry ở types/telemetry.ts (có risk_level, risk_score, fps.{camera,face,phone}, latency_ms.{face,phone}, face_detected, error).

Việc cần làm:
1. app/camera/page.tsx ('use client') + components/camera/live-view.tsx (và file con nếu cần), CSS trong app/camera/camera.css (dùng token CSS có giá trị dự phòng, ví dụ var(--surface, #fff)). Bố cục:
   - Đầu trang: "DriverGuard · Camera" bên trái; bên phải trạng thái kết nối bằng chữ + hình vuông 8 px (không pill) và hai liên kết văn bản cao ≥ 44 px: "Tài xế" (tới "/") và "Giám sát" (tới "/monitor").
   - Khung video: tỉ lệ 4:3, rộng tối đa 960 px, căn giữa, viền 1 px --border, bo 6 px, nền đen. Ảnh object-fit: contain.
   - Trạng thái trên khung video, chỉ một trong các lớp phủ chữ (nền --surface, chữ --text, căn giữa): chưa kết nối backend ("Chưa kết nối tới backend…"); đã kết nối nhưng chưa nhận khung hình đầu ("Đang chờ hình từ camera…", dùng onLoad của <img> để biết đã có hình); `telemetry.error === "camera_unavailable"` ("Không mở được camera. Kiểm tra camera có đang được ứng dụng khác dùng không."); `!telemetry.face_detected` có hình thì KHÔNG phủ lên hình, chỉ hiện dòng "Không thấy khuôn mặt" ở dưới khung.
   - Dưới khung video, một hàng thông tin gọn: mức rủi ro (nhãn vuông bo 4 px nền token *-bg, chữ token màu, có biểu tượng nhỏ SVG, KHÔNG chỉ dựa vào màu) + điểm; FPS camera/mặt/điện thoại; độ trễ mặt/điện thoại (ms). Số dùng tabular-nums.
   - Nút "Toàn màn hình" (Fullscreen API trên phần tử khung video; ẩn nút nếu trình duyệt không hỗ trợ; nhấn Esc thoát là hành vi trình duyệt). Nút chữ nhật bo 6 px, viền 1 px, cao ≥ 44 px, có aria-label.
   - Tiết kiệm băng thông: khi tab bị ẩn (document.visibilityState === "hidden") ngắt luồng bằng cách bỏ src của <img>, khi hiện lại thì gán lại src (kèm tham số `&t=<Date.now()>` để mở luồng mới).
   - Chú thích nhỏ dưới cùng (14 px, --text-muted): "Hình có chú thích nhận diện từ AI worker. Không lưu hình." (đúng sự thật: backend không lưu hình).
2. Thêm liên kết "Camera" vào điều hướng: (a) trong app/monitor/page.tsx hoặc components/monitor/monitor-ui.tsx cạnh liên kết "Chế độ tài xế" ở đầu trang; (b) trong components/driver/status-screen.tsx và start-gate.tsx cạnh liên kết "Giám sát" ở cuối trang (liên kết văn bản gạch chân, vùng bấm ≥ 48 px, KHÔNG làm đổi logic nào của hai file này).
3. Giữ nguyên toàn bộ logic, API, kiểu dữ liệu, test hiện có. Không thêm dependency. Truy cập bàn phím tốt, alt cho ảnh ("Luồng camera tài xế").
4. Ngoài phạm vi: tính năng bật/tắt chú thích (cần đổi backend), ghi hình/chụp ảnh, nhiều camera.

Do Not Modify: mọi file ngoài danh sách: app/camera/*, components/camera/*, và việc thêm liên kết ở app/monitor/page.tsx (hoặc components/monitor/monitor-ui.tsx), components/driver/status-screen.tsx, components/driver/start-gate.tsx. Cấm sửa: lib/*, types/*, app/globals.css, app/layout.tsx, package.json, apps/backend, ai/, docs/ (chỉ đọc).

Tiêu chí nghiệm thu: `npm run lint`, `npm run build`, `npm test` pass; route /camera có trong danh sách build; không có glow/gradient/rounded-full/pill/font-weight ≥ 700/màu zinc-* trong file mới.

## OUTPUT_START
1. Danh sách file đã tạo/sửa
2. Giải thích ngắn (tối đa 8 dòng)
3. Rủi ro / điểm chưa chắc
## OUTPUT_END
