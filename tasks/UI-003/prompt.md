Tự viết code TRỰC TIẾP bằng công cụ ghi file. KHÔNG giao subagent, KHÔNG chạy lệnh shell (Claude sẽ chạy lint/build/test). Khi ghi xong, trả lời theo định dạng ở cuối (bắt đầu bằng "## OUTPUT_START", kết thúc bằng "## OUTPUT_END").

Task UI-003: THIẾT KẾ LẠI giao diện chế độ Tài xế để hết "mùi AI" (neon phát sáng, vòng tròn biểu tượng, chữ xanh khổng lồ, câu quảng cáo, pill). ĐỌC KỸ docs/ui-design-spec.md và làm đúng từng mục (mục 1 cấm, 2 phông chữ, 3 token màu, 4 màn hình Tài xế, 6 yêu cầu chung).

Bạn sở hữu (được sửa): apps/web/app/layout.tsx, apps/web/app/globals.css, apps/web/components/driver/start-gate.tsx, status-screen.tsx, calibration-ring.tsx.
Việc cần làm:
1. layout.tsx: thay Geist bằng Inter với subsets ["latin","vietnamese"] qua next/font/google (lỗi hiện tại: thiếu subset vietnamese nên dấu tiếng Việt rơi sang phông khác). Giữ lang="vi", title "DriverGuard".
2. globals.css: khai báo toàn bộ token ở mục 3 của spec (sáng + tối theo prefers-color-scheme), reset đơn giản, focus ring, tabular-nums; XÓA hết lớp glow (glow-border-*, box-shadow phát sáng, keyframes nhấp nháy viền). Chỉ giữ animation nền chậm cho DANGER leo thang theo spec, tắt khi prefers-reduced-motion. Các lớp CSS cho trang /monitor (app/monitor/monitor.css) KHÔNG phải của bạn, nhưng giữ các tên biến token để chúng dùng được.
3. Viết lại start-gate.tsx, status-screen.tsx, calibration-ring.tsx theo mục 4 của spec: nền đặc theo mức (bình thường yên tĩnh; WARNING nền vàng; DANGER nền đỏ), KHÔNG glow, KHÔNG vòng tròn biểu tượng lớn, KHÔNG câu giới thiệu, nút chữ nhật theo spec.
4. GIỮ NGUYÊN toàn bộ logic: props, useAlertSound/alertStage/activeReasons, các hàm gọi postMute/postCalibrate, tính stage bằng setInterval + ref, vòng đếm KHÔNG gọi postCalibrate, role="alert"/aria-live khi DANGER. Giữ chữ nguyên nhân hiện có.
5. Nút "Tắt tiếng 15 giây" vẫn hiển thị "Đang gửi…" và "Đã tắt tiếng" như hiện tại (phản hồi tức thì).

Do Not Modify: mọi file ngoài danh sách bạn sở hữu, đặc biệt lib/*, types/*, app/page.tsx, app/monitor/*, components/monitor/*, components/{charts,controls,driver-status,event-list,risk-meter,video-feed}/*, package.json, tsconfig.json, apps/backend, ai/, docs/ (chỉ đọc).
Out Of Scope: chế độ Giám sát (/monitor), đổi logic, thêm dependency, thêm tính năng.

Tiêu chí nghiệm thu: `npm run lint`, `npm run build`, `npm test` pass; không còn box-shadow phát sáng/gradient/rounded-full/pill/font-weight ≥ 700 trong các file bạn sở hữu; token khai báo đủ; tương phản đạt ở cả sáng và tối.

## OUTPUT_START
1. Danh sách file đã sửa
2. Giải thích ngắn (tối đa 8 dòng)
3. Rủi ro / điểm chưa chắc
## OUTPUT_END
