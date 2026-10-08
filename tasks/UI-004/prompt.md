Nhiệm vụ UI-004: THIẾT KẾ LẠI giao diện chế độ Giám sát (/monitor) để hết "mùi AI" (thẻ bo lớn, pill, màu lẫn lộn, nền navy). ĐỌC KỸ docs/ui-design-spec.md và làm đúng mục 1 (cấm), 2, 3 (token màu), 5 (màn hình Giám sát), 6. Bạn được chạy lệnh trong apps/web (npm run lint / build / test). Không thêm dependency.

Quan trọng: một nhân viên khác (Gemini) đang làm song song app/globals.css và app/layout.tsx để khai báo token màu (biến CSS --bg, --surface, --border, --text, --text-muted, --accent, --ok, --ok-bg, --warn, --warn-bg, --warn-solid, --danger, --danger-bg, --danger-solid, --radius-sm, --radius, --radius-lg theo spec mục 3) và phông Inter. BẠN KHÔNG SỬA hai file đó; hãy dùng biến CSS đó với giá trị dự phòng, ví dụ `var(--surface, #fff)`, để chạy được cả khi chưa có token.

Bạn sở hữu (được sửa): apps/web/app/monitor/page.tsx, apps/web/app/monitor/monitor.css, apps/web/components/monitor/*, và (CHỈ phần giao diện, không logic) apps/web/components/{charts,controls,driver-status,event-list,risk-meter,video-feed}/* vì chúng chỉ dùng ở /monitor. Hãy chuyển chúng sang CSS dùng token (có thể dùng monitor.css) và bỏ các lớp Tailwind màu zinc/rounded-xl/rounded-full.

Việc cần làm:
1. Đầu trang: "DriverGuard · Giám sát" bên trái, bên phải trạng thái kết nối bằng chữ có hình vuông 8 px (không viên thuốc); liên kết "Chế độ tài xế" cao ≥ 44 px.
2. Các khối dạng khung phẳng theo spec mục 5 (surface + viền 1 px + bo 6 px, không đổ bóng, không rounded-xl). Tiêu đề khối 14 px/600.
3. Nhãn mức (NORMAL/WARNING/DANGER) và huy hiệu trạng thái tài xế: nhãn vuông bo 4 px dùng token *-bg / chữ màu tương ứng, có biểu tượng nhỏ SVG hoặc ký hiệu để không chỉ dựa vào màu; BỎ pill.
4. Bảng sự kiện: bảng thật, hàng cao ≥ 44 px, số căn phải + tabular-nums, hover nền --bg. Giữ drawer chi tiết và logic hiện có.
5. Dòng thời gian rủi ro và biểu đồ EAR/MAR: một màu nhấn --accent cho đường chính, dải mức bằng --ok-bg/--warn-bg/--danger-bg nhạt, chữ trục 12 px --text-muted.
6. Thanh rủi ro (RiskMeter): thanh phẳng cao 8 px, màu theo mức; bỏ banner đỏ chớp nháy nếu có, thay bằng một dòng nhãn nguy hiểm tĩnh có biểu tượng.
7. Nút theo spec: chữ nhật bo 6 px, cao ≥ 44 px; nút chính nền --accent chữ trắng; còn lại viền 1 px.
8. GIỮ NGUYÊN toàn bộ logic, props, API, kiểu dữ liệu, test. Chỉ đổi giao diện (class, CSS, JSX, chữ hiển thị). Bỏ mọi câu giới thiệu/phụ đề thừa (ví dụ "Chấm tròn biểu thị sự kiện…" có thể rút gọn).

Cấm sửa: app/layout.tsx, app/globals.css, app/page.tsx, components/driver/*, lib/* (trừ khi bắt buộc; nếu phải sửa thì nêu rõ lý do trong báo cáo), types/*, package.json, tsconfig.json, apps/backend, ai/, docs/ (chỉ đọc).
Ngoài phạm vi: chế độ Tài xế, đổi logic, thêm tính năng, dependency.

Nghiệm thu: `npm run lint`, `npm run build`, `npm test` pass; không còn glow/gradient/rounded-full/pill/font-weight ≥ 700/zinc-* trong các file bạn sở hữu; chạy được cả khi token chưa có (giá trị dự phòng). Báo cáo ngắn: file đã sửa, kết quả lệnh, điểm chưa chắc.
