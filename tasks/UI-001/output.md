1. Danh sách file đã tạo/sửa:
- [`apps/web/lib/reasons.ts`](file:///D:/D%E1%BB%B1%20%C3%81n%20C%C3%A1%20Nh%C3%A2n/DriverGuard_Documentation/apps/web/lib/reasons.ts) (tạo mới)
- [`apps/web/lib/reasons.test.ts`](file:///D:/D%E1%BB%B1%20%C3%81n%20C%C3%A1%20Nh%C3%A2n/DriverGuard_Documentation/apps/web/lib/reasons.test.ts) (tạo mới)
- [`apps/web/lib/alert-level.ts`](file:///D:/D%E1%BB%B1%20%C3%81n%20C%C3%A1%20Nh%C3%A2n/DriverGuard_Documentation/apps/web/lib/alert-level.ts) (tạo mới)
- [`apps/web/lib/alert-level.test.ts`](file:///D:/D%E1%BB%B1%20%C3%81n%20C%C3%A1%20Nh%C3%A2n/DriverGuard_Documentation/apps/web/lib/alert-level.test.ts) (tạo mới)
- [`apps/web/lib/useAlertSound.ts`](file:///D:/D%E1%BB%B1%20%C3%81n%20C%C3%A1%20Nh%C3%A2n/DriverGuard_Documentation/apps/web/lib/useAlertSound.ts) (tạo mới)
- [`apps/web/components/driver/calibration-ring.tsx`](file:///D:/D%E1%BB%B1%20%C3%81n%20C%C3%A1%20Nh%C3%A2n/DriverGuard_Documentation/apps/web/components/driver/calibration-ring.tsx) (tạo mới)
- [`apps/web/components/driver/start-gate.tsx`](file:///D:/D%E1%BB%B1%20%C3%81n%20C%C3%A1%20Nh%C3%A2n/DriverGuard_Documentation/apps/web/components/driver/start-gate.tsx) (tạo mới)
- [`apps/web/components/driver/status-screen.tsx`](file:///D:/D%E1%BB%B1%20%C3%81n%20C%C3%A1%20Nh%C3%A2n/DriverGuard_Documentation/apps/web/components/driver/status-screen.tsx) (tạo mới)
- [`apps/web/app/page.tsx`](file:///D:/D%E1%BB%B1%20%C3%81n%20C%C3%A1%20Nh%C3%A2n/DriverGuard_Documentation/apps/web/app/page.tsx) (viết lại hoàn toàn cho Chế độ Tài xế)
- [`apps/web/app/globals.css`](file:///D:/D%E1%BB%B1%20%C3%81n%20C%C3%A1%20Nh%C3%A2n/DriverGuard_Documentation/apps/web/app/globals.css) (thêm CSS variables, viền phát sáng inset glow và keyframes nhấp nháy tôn trọng prefers-reduced-motion)
- [`apps/web/package.json`](file:///D:/D%E1%BB%B1%20%C3%81n%20C%C3%A1%20Nh%C3%A2n/DriverGuard_Documentation/apps/web/package.json) (thêm script `"test": "node --test lib/"`)

2. Giải thích ngắn:
- Triển khai 2 module thuần [`reasons.ts`](file:///D:/D%E1%BB%B1%20%C3%81n%20C%C3%A1%20Nh%C3%A2n/DriverGuard_Documentation/apps/web/lib/reasons.ts) và [`alert-level.ts`](file:///D:/D%E1%BB%B1%20%C3%81n%20C%C3%A1%20Nh%C3%A2n/DriverGuard_Documentation/apps/web/lib/alert-level.ts) chỉ dùng `import type` tương đối, sẵn sàng chạy với `node --test`.
- Viết bộ unit test đầy đủ trong [`reasons.test.ts`](file:///D:/D%E1%BB%B1%20%C3%81n%20C%C3%A1%20Nh%C3%A2n/DriverGuard_Documentation/apps/web/lib/reasons.test.ts) và [`alert-level.test.ts`](file:///D:/D%E1%BB%B1%20%C3%81n%20C%C3%A1%20Nh%C3%A2n/DriverGuard_Documentation/apps/web/lib/alert-level.test.ts) dùng `node:test` và `node:assert/strict`.
- Tạo hook [`useAlertSound`](file:///D:/D%E1%BB%B1%20%C3%81n%20C%C3%A1%20Nh%C3%A2n/DriverGuard_Documentation/apps/web/lib/useAlertSound.ts) phát âm thanh bằng Web Audio API oscillator theo nhịp stage, tự dọn dẹp interval khi đổi stage/unmount và tắt hoàn toàn khi "off".
- Màn hình [`StartGate`](file:///D:/D%E1%BB%B1%20%C3%81n%20C%C3%A1%20Nh%C3%A2n/DriverGuard_Documentation/apps/web/components/driver/start-gate.tsx) có nút bấm lớn ≥ 64px mở khóa audio policy, sau đó mới chuyển sang giám sát.
- Màn hình [`StatusScreen`](file:///D:/D%E1%BB%B1%20%C3%81n%20C%C3%A1%20Nh%C3%A2n/DriverGuard_Documentation/apps/web/components/driver/status-screen.tsx) tối giản trong xe: viền inset glow đổi theo mức (xanh, vàng, đỏ nhấp nháy, xám mất kết nối), chữ trạng thái lớn kèm biểu tượng SVG, tối đa 2 nguyên nhân, chip kết nối và điểm rủi ro nhỏ.
- Nút "Tắt tiếng 15 giây" lớn (chiều cao ≥ 64px), nút "Hiệu chuẩn lại" nhỏ hơn và liên kết nhỏ tới `/monitor`.
- Lớp phủ [`CalibrationRing`](file:///D:/D%E1%BB%B1%20%C3%81n%20C%C3%A1%20Nh%C3%A2n/DriverGuard_Documentation/apps/web/components/driver/calibration-ring.tsx) hiển thị đếm 4s bằng vòng tròn SVG khi có mặt và chưa hiệu chuẩn; tự đặt lại nếu mất mặt và ẩn khi đã hiệu chuẩn.
- Theo dõi `dangerSinceMs` và định kỳ cập nhật `nowMs` mỗi 500ms để leo thang âm thanh lên `danger_escalated` ở mốc 5 giây.
- Đảm bảo tính tiếp cận: `role="alert"` + `aria-live="assertive"` khi DANGER, bàn phím điều hướng được với focus ring, không dùng `any` và không console.log.

3. Rủi ro / điểm chưa chắc:
- Chưa thể chạy lệnh kiểm chứng trực tiếp (`npm run build`, `npm run lint`, `npm test`) do tuân thủ yêu cầu không chạy lệnh shell; cần Claude kiểm tra kết quả build/test sau khi nhận bàn giao.
- Việc thực thi `node --test lib/` phụ thuộc vào phiên bản Node.js môi trường máy (cần Node.js hỗ trợ type stripping để chạy trực tiếp file `.ts`).
- Web Audio API trên trình duyệt mobile có thể bị treo (suspended) nếu ứng dụng chuyển sang nền lâu rồi quay lại mà chưa có tương tác chạm bổ sung.
