1. Danh sách file đã sửa:
- [`apps/web/app/layout.tsx`](file:///D:/D%E1%BB%B1%20%C3%81n%20C%C3%A1%20Nh%C3%A2n/DriverGuard_Documentation/apps/web/app/layout.tsx)
- [`apps/web/app/globals.css`](file:///D:/D%E1%BB%B1%20%C3%81n%20C%C3%A1%20Nh%C3%A2n/DriverGuard_Documentation/apps/web/app/globals.css)
- [`apps/web/components/driver/start-gate.tsx`](file:///D:/D%E1%BB%B1%20%C3%81n%20C%C3%A1%20Nh%C3%A2n/DriverGuard_Documentation/apps/web/components/driver/start-gate.tsx)
- [`apps/web/components/driver/status-screen.tsx`](file:///D:/D%E1%BB%B1%20%C3%81n%20C%C3%A1%20Nh%C3%A2n/DriverGuard_Documentation/apps/web/components/driver/status-screen.tsx)
- [`apps/web/components/driver/calibration-ring.tsx`](file:///D:/D%E1%BB%B1%20%C3%81n%20C%C3%A1%20Nh%C3%A2n/DriverGuard_Documentation/apps/web/components/driver/calibration-ring.tsx)
- [`MEMORY.md`](file:///D:/D%E1%BB%B1%20%C3%81n%20C%C3%A1%20Nh%C3%A2n/DriverGuard_Documentation/MEMORY.md) (cập nhật nhật ký theo quy ước)

2. Giải thích ngắn:
- Đổi phông hệ thống sang `Inter` với `subsets: ["latin", "vietnamese"]` qua `next/font/google`, giữ `lang="vi"` và title "DriverGuard".
- Khai báo đầy đủ token màu (sáng mặc định, tối theo `prefers-color-scheme`), reset, focus ring chuẩn 2px và `tabular-nums` trong [`globals.css`](file:///D:/D%E1%BB%B1%20%C3%81n%20C%C3%A1%20Nh%C3%A2n/DriverGuard_Documentation/apps/web/app/globals.css).
- Xóa sạch toàn bộ glow, box-shadow phát sáng, viền nhấp nháy; chỉ giữ animation nền chậm cho DANGER leo thang (`stage === "danger_escalated"`), tự tắt khi `prefers-reduced-motion`.
- Viết lại [`start-gate.tsx`](file:///D:/D%E1%BB%B1%20%C3%81n%20C%C3%A1%20Nh%C3%A2n/DriverGuard_Documentation/apps/web/components/driver/start-gate.tsx) tối giản: bỏ biểu tượng khiên/mô tả quảng cáo, nút chữ nhật cao 64px nền `--accent`, ghi chú 14px và link Giám sát ≥48px.
- Viết lại [`status-screen.tsx`](file:///D:/D%E1%BB%B1%20%C3%81n%20C%C3%A1%20Nh%C3%A2n/DriverGuard_Documentation/apps/web/components/driver/status-screen.tsx): NORMAL nền `--bg` yên tĩnh với ô vuông 12px `--ok`; WARNING nền `--warn-solid` chữ đen 96px; DANGER nền `--danger-solid` chữ trắng kèm tam giác SVG nét 4px.
- Nút "Tắt tiếng 15 giây" chữ nhật cao 64px bo 8px, viền tương phản nền (viền trắng trên DANGER), giữ nguyên phản hồi tức thì "Đang gửi…" / "Đã tắt tiếng".
- Viết lại [`calibration-ring.tsx`](file:///D:/D%E1%BB%B1%20%C3%81n%20C%C3%A1%20Nh%C3%A2n/DriverGuard_Documentation/apps/web/components/driver/calibration-ring.tsx) với vòng SVG nét 4px không glow/không backdrop-blur, chữ 28px, đếm ngược tại client và không gọi API thừa.
- Giữ nguyên 100% logic: props, API handlers (`postMute`, `postCalibrate`), tính stage với interval + ref, `useAlertSound` và `role="alert"` / `aria-live`.

3. Rủi ro / điểm chưa chắc:
- Không chạy lệnh shell cục bộ theo chỉ đạo nên việc kiểm tra build/lint/test sẽ do Claude thực hiện; cần xác nhận Next.js tải phông Inter trực tuyến mượt mà không gặp rào cản mạng nội bộ.
