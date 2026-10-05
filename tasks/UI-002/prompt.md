Nhiệm vụ UI-002: làm CHẾ ĐỘ GIÁM SÁT cho dashboard DriverGuard tại apps/web (Next.js 16 App Router, React 19, TypeScript, Tailwind 4). Bạn được phép chạy lệnh trong apps/web (npm run lint, npm run build, npm test). Không thêm dependency mới.

Bối cảnh: một nhân viên khác (Gemini) đang viết lại apps/web/app/page.tsx thành "Chế độ tài xế" cùng lúc. Bạn là bên DUY NHẤT sở hữu route /monitor. Dashboard hiện tại (sẽ bị Gemini ghi đè ở app/page.tsx) lấy từ git: `git show HEAD:apps/web/app/page.tsx`.

Việc cần làm:
1. app/monitor/page.tsx ('use client'): chuyển dashboard hiện tại sang đây (giữ nguyên các thành phần: VideoFeed, Controls, RiskMeter, DriverStatus, EarMarChart, EventList) rồi bổ sung các phần mới dưới đây. Thêm liên kết nhỏ "Chế độ tài xế" (next/link) về "/".
2. Dòng thời gian rủi ro (components/monitor/risk-timeline.tsx + lib/useRiskHistory.ts + lib/timeline.ts): lưu điểm `risk_score` theo thời gian của 5 phút gần nhất (tối đa ~1 điểm/giây, giảm mẫu), vẽ bằng SVG thuần (không thư viện): đường điểm rủi ro, dải nền theo mức (NORMAL < 40, WARNING < 70, DANGER ≥ 70), và các đánh dấu sự kiện (chấm theo `event_type`, lấy từ `telemetry.events` khi đến). Trục thời gian "-5 phút ... bây giờ". Hàm thuần trong lib/timeline.ts: `downsample(points, maxPoints)`, `pruneOlderThan(points, nowMs, windowMs)`, `levelBand(score)`; mỗi hàm có test.
3. Bảng sự kiện có chi tiết (components/monitor/event-table.tsx + components/monitor/event-drawer.tsx): lấy từ getEvents() (lib/api.ts) làm mới mỗi 3 giây; bấm vào một dòng mở ngăn bên (drawer, có nút đóng, đóng bằng phím Esc, focus trap đơn giản) hiện: loại sự kiện (tên tiếng Việt), thời điểm, thời lượng (giây), mức, điểm rủi ro, độ tin cậy (%), nguyên nhân (`reason`). KHÔNG sửa components/event-list/event-list.tsx cũ (có thể không dùng nữa ở /monitor).
4. Bảng sức khỏe hệ thống (components/monitor/system-health.tsx): hiển thị FPS (camera/mặt/điện thoại), độ trễ (mặt/điện thoại), trạng thái kết nối WebSocket, và kết quả GET `${API_URL}/api/v1/health` (ai_worker_alive, camera_connected, status) làm mới mỗi 5 giây. Thêm hàm `getHealth()` vào một file MỚI lib/health.ts (không sửa lib/api.ts; import API_URL từ lib/api.ts).
5. Giao diện tiếng Việt, tối, responsive, truy cập bàn phím (nút có nhãn, drawer có role="dialog" aria-modal), không dùng `any`, không console.log.
6. Test bằng `node:test` + `node:assert/strict` có sẵn (không thêm thư viện): lib/timeline.test.ts. Module thuần chỉ được `import type` (đường dẫn tương đối có đuôi .ts, KHÔNG dùng alias "@/"), để `node --test` chạy được. Thêm script "test" vào apps/web/package.json nếu chưa có: `"test": "node --test lib/"` (nếu Gemini đã thêm rồi thì giữ nguyên, đừng ghi đè hay trùng).

Cấm sửa: apps/backend, ai/, docs/, scripts/, state/, memory/, app/page.tsx (của Gemini), app/layout.tsx, app/globals.css, types/telemetry.ts, lib/api.ts, lib/useTelemetry.ts, components/driver/*, lib/reasons.ts, lib/alert-level.ts, lib/useAlertSound.ts, các component cũ (charts, controls, driver-status, event-list, risk-meter, video-feed), package-lock.json.

Ngoài phạm vi: trang cài đặt ngưỡng, tổng kết hành trình, mọi thay đổi backend/API, thêm dependency.

Nghiệm thu: `npm run lint` và `npm run build` trong apps/web không lỗi (nếu build lỗi do file của Gemini chưa xong, nêu rõ và chỉ báo lỗi thuộc phần của bạn); `npm test` pass phần timeline. Báo cáo ngắn: file đã tạo, kết quả lệnh, điểm chưa chắc.

Nguyên tắc thiết kế BẮT BUỘC (sếp yêu cầu: đơn giản, dễ dùng; tham khảo Google Material Design 3 và Alibaba Ant Design):
- Đơn giản trước tiên: mỗi màn hình chỉ làm một việc chính; bỏ mọi yếu tố không cần cho việc đó. Ít chữ, ít màu, nhiều khoảng trắng; dùng một thang cỡ chữ và khoảng cách nhất quán (bội số của 4 px). (Ant Design: "Tự nhiên" – giảm tải nhận thức; "Chắc chắn" – dùng thành phần nhất quán.)
- Phản hồi tức thì (Ant Design: "Có ý nghĩa"): bấm nút phải đổi trạng thái ngay (đang gửi, đã tắt tiếng...), mọi trạng thái rỗng/lỗi/mất kết nối có chữ giải thích rõ và việc cần làm.
- Vùng bấm (Google Material): mọi nút/liên kết tương tác cao tối thiểu 48 px; nút chính ở màn hình tài xế ≥ 64 px. Có focus ring rõ khi dùng bàn phím.
- Tương phản (Google Material 3): chữ ≥ 4.5:1, thành phần giao diện ≥ 3:1.
- KHÔNG chỉ dựa vào màu để báo trạng thái: mỗi trạng thái có thêm biểu tượng SVG tự vẽ (✓ / ! / ⚠, dùng inline SVG, không thư viện icon) và nhãn chữ, dùng cùng một màu cho cùng một ý nghĩa ở mọi nơi (xanh = bình thường, vàng = chú ý, đỏ = nguy hiểm).
- Hệ thống thiết kế nhất quán: định nghĩa màu và bán kính bo góc bằng biến CSS/Tailwind một chỗ, không rải màu hex khắp nơi.
- Tôn trọng prefers-reduced-motion.
