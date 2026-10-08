Tự viết code TRỰC TIẾP bằng công cụ ghi file. KHÔNG giao cho subagent, KHÔNG chạy lệnh shell (không npm, không node) — Claude sẽ chạy build/test sau. Khi đã ghi xong tất cả file, trả lời theo định dạng ở cuối, bắt đầu bằng "## OUTPUT_START" và kết thúc bằng "## OUTPUT_END".

Mục tiêu (task UI-001):
Làm CHẾ ĐỘ TÀI XẾ cho dashboard DriverGuard (apps/web, Next.js 16 App Router, React 19, TypeScript, Tailwind 4): màn hình trong xe, tối giản, đọc nhanh, có cảnh báo âm thanh leo thang và hướng dẫn hiệu chuẩn. Dashboard hiện tại sẽ do người khác chuyển sang /monitor (không phải việc của bạn).

Kiến trúc liên quan:
- Backend phát telemetry qua WebSocket; hook sẵn có `useTelemetry()` (lib/useTelemetry.ts) trả `{ telemetry, connected, history }`. Kiểu `Telemetry`, `RiskLevel` ở types/telemetry.ts. `risk_level` thuộc NORMAL | WARNING | DANGER. Telemetry có các cờ: face_detected, calibrated, muted, eyes_closed, yawning, looking_away, looking_down, phone_usage, risk_score; `events` là danh sách sự kiện mới (mỗi sự kiện có event_type, reason).
- API sẵn có ở lib/api.ts: `postCalibrate()`, `postMute(seconds)`. Khi tắt tiếng, backend đặt `telemetry.muted = true` trong 15 giây.
- Giao diện tiếng Việt (có đủ dấu). Giao diện tối.

Existing Files (đã có, được phép đọc):
- apps/web/app/page.tsx — dashboard hiện tại; bạn sẽ viết lại hoàn toàn thành chế độ Tài xế (dashboard cũ vẫn còn trong git và sẽ được chuyển sang /monitor bởi người khác)
- apps/web/app/layout.tsx, app/globals.css
- apps/web/lib/api.ts, lib/useTelemetry.ts, types/telemetry.ts
- apps/web/components/{charts,controls,driver-status,event-list,risk-meter,video-feed}/*

Việc cần làm:
1. KHÔNG tạo hay sửa app/monitor/* — trang /monitor do một nhân viên khác làm song song. Chỉ cần liên kết tới "/monitor" bằng next/link.
2. Viết lại app/page.tsx thành CHẾ ĐỘ TÀI XẾ ('use client'):
   - Màn hình đầu tiên (components/driver/start-gate.tsx): nút lớn "Bắt đầu giám sát" để mở khoá âm thanh của trình duyệt (autoplay policy). Chỉ sau khi bấm mới hiện màn hình giám sát. Trong lúc chưa bấm vẫn dùng useTelemetry nhưng KHÔNG phát âm thanh.
   - Màn hình giám sát (components/driver/status-screen.tsx): toàn màn hình (min-h-dvh), nền gần đen. Viền toàn màn hình phát sáng theo mức: NORMAL xanh lá, WARNING vàng, DANGER đỏ (nhấp nháy chậm; thêm class CSS trong globals.css, dùng box-shadow inset; tôn trọng `prefers-reduced-motion` bằng cách tắt animation). Ở giữa là dòng trạng thái rất lớn: "Đang theo dõi" (NORMAL), "Chú ý" (WARNING), "NGUY HIỂM" (DANGER). Dưới đó hiện tối đa 2 nguyên nhân (xem lib/reasons.ts), chữ lớn. Điểm rủi ro hiện nhỏ ở góc trên bên phải; chip trạng thái kết nối nhỏ ở góc trên bên trái.
   - Không hiện camera, biểu đồ, số liệu kỹ thuật.
   - Nút "Tắt tiếng 15 giây" LỚN ở phía dưới (gọi postMute(15)); khi `telemetry.muted` hiện "Đã tắt tiếng". Nút nhỏ hơn "Hiệu chuẩn lại" (gọi postCalibrate()). Một liên kết rất nhỏ "Giám sát" tới /monitor.
   - Trạng thái đặc biệt: chưa có telemetry -> "Đang chờ dữ liệu từ AI worker…"; mất kết nối -> "Mất kết nối — đang thử lại…" (viền xám); `telemetry.error === "camera_unavailable"` -> "Không mở được camera".
3. Hiệu chuẩn có hướng dẫn (components/driver/calibration-ring.tsx): khi `connected && !telemetry.calibrated && telemetry.face_detected`, hiện lớp phủ giữa màn hình: vòng tròn SVG đếm 4 giây (tiến độ chạy từ 0 đến 100%), chữ "Nhìn thẳng phía trước". Bộ đếm bắt đầu khi điều kiện này thành đúng và được đặt lại nếu mất mặt. Khi `calibrated` thành true thì ẩn. Nếu `!face_detected` và chưa hiệu chuẩn hiện "Không thấy khuôn mặt". Lưu ý: khi chưa hiệu chuẩn thì KHÔNG phát âm thanh cảnh báo.
4. Âm thanh (lib/useAlertSound.ts) bằng Web Audio API (tạo bằng oscillator, KHÔNG dùng file âm thanh): hook `useAlertSound(stage: AlertStage, enabled: boolean)`. Chỉ phát khi `enabled` (đã bấm Bắt đầu). Dùng một AudioContext duy nhất (tạo/resume trong sự kiện bấm "Bắt đầu" hoặc khi enabled chuyển true), setInterval theo `beepPattern(stage)`, dọn dẹp interval khi stage đổi hoặc unmount. Dừng hẳn khi stage = "off".
5. Hai module thuần (KHÔNG import gì ngoài `import type`, để chạy được bằng `node --test`; viết import type ở dạng `import type { ... } from "../types/telemetry"` dùng đường dẫn tương đối, KHÔNG dùng alias "@/"):
   - lib/reasons.ts: `export function activeReasons(t: Telemetry): string[]`. Thứ tự ưu tiên và nhãn: eyes_closed -> "Nhắm mắt kéo dài"; phone_usage -> "Đang dùng điện thoại"; looking_away -> "Quay đầu lệch hướng"; looking_down -> "Cúi đầu"; yawning -> "Ngáp"; !face_detected -> "Không thấy khuôn mặt". Trả về tất cả cái đúng theo thứ tự đó (người gọi tự cắt còn 2).
   - lib/alert-level.ts: `export type AlertStage = "off" | "caution" | "danger" | "danger_escalated"`; `export function alertStage(input: { level: RiskLevel; muted: boolean; connected: boolean; calibrated: boolean; dangerSinceMs: number | null; nowMs: number }): AlertStage` với quy tắc: nếu !connected hoặc muted hoặc !calibrated -> "off"; level NORMAL -> "off"; WARNING -> "caution"; DANGER -> "danger" nếu dangerSinceMs === null hoặc nowMs - dangerSinceMs < 5000, ngược lại "danger_escalated". `export function beepPattern(stage: AlertStage): { frequencyHz: number; durationMs: number; intervalMs: number; volume: number } | null`: off -> null; caution -> {660, 200, 4000, 0.15}; danger -> {880, 250, 1000, 0.3}; danger_escalated -> {1100, 300, 500, 0.5}.
   - Ở status-screen theo dõi `dangerSinceMs` bằng useRef/useState: đặt thành Date.now() khi level chuyển sang DANGER, null khi rời DANGER; cập nhật `nowMs` mỗi 500 ms để stage leo thang kịp lúc.
6. Test (dùng `node:test` và `node:assert/strict` có sẵn, KHÔNG thêm thư viện): lib/reasons.test.ts và lib/alert-level.test.ts. Phủ: thứ tự và nhãn lý do; không có lý do khi mọi cờ tắt và có mặt; mọi nhánh của alertStage (off khi mất kết nối / tắt tiếng / chưa hiệu chuẩn; caution; danger; danger_escalated đúng ở mốc 5000 ms); beepPattern từng stage. Thêm vào apps/web/package.json một script "test": "node --test lib/" (không đổi gì khác trong package.json). Import trong test dùng đường dẫn tương đối kèm đuôi ".ts" (ví dụ `from "./reasons.ts"`).
7. Yêu cầu chất lượng: truy cập được bằng bàn phím, nút có `aria-label`/nhãn rõ; vùng cảnh báo có `role="alert"` + `aria-live="assertive"` khi DANGER; tương phản cao; không dùng `any`; không để lại console.log.

Do Not Modify (cấm sửa):
- apps/web/app/monitor/* và apps/web/components/monitor/* (do người khác làm song song)
- Mọi thứ ngoài apps/web (apps/backend, ai/, docs/, scripts/, state/, memory/, tasks/ trừ tasks/UI-001/*).
- apps/web/types/telemetry.ts, lib/api.ts, lib/useTelemetry.ts
- apps/web/components/{charts,controls,driver-status,event-list,risk-meter,video-feed}/* (dùng lại ở /monitor, không sửa)
- apps/web/package-lock.json, next.config.ts, tsconfig.json

Out Of Scope (không làm trong task này):
- Chế độ Giám sát nâng cao (dòng thời gian rủi ro, ngăn chi tiết sự kiện, bảng sức khỏe hệ thống) — để task sau.
- Trang cài đặt ngưỡng, tổng kết hành trình, mọi thay đổi backend/API.
- Thêm bất kỳ dependency nào (vitest, framer-motion, thư viện âm thanh, icon...).

Ràng buộc:
- Giữ nguyên kiến trúc hiện có và hợp đồng API; chỉ dùng các API sẵn có.
- Dùng Tailwind 4 như dự án hiện tại; viết CSS riêng chỉ cho hiệu ứng viền và nhấp nháy trong app/globals.css.
- Next.js 16: nếu không chắc về một API của Next, dùng cách đơn giản nhất (client component thuần, next/link).

Tiêu chí nghiệm thu:
- `npm run build` và `npm run lint` trong apps/web không lỗi; `npm test` chạy 2 file test và pass.
- "/" hiện nút Bắt đầu giám sát, sau đó là màn hình tài xế đúng mô tả; "/" có liên kết nhỏ tới /monitor.
- Không phát âm thanh khi chưa bấm Bắt đầu, khi muted, khi chưa hiệu chuẩn, khi mất kết nối.



Nguyên tắc thiết kế BẮT BUỘC (sếp yêu cầu: đơn giản, dễ dùng; tham khảo Google Material Design 3 và Alibaba Ant Design):
- Đơn giản trước tiên: mỗi màn hình chỉ làm một việc chính; bỏ mọi yếu tố không cần cho việc đó. Ít chữ, ít màu, nhiều khoảng trắng; dùng một thang cỡ chữ và khoảng cách nhất quán (bội số của 4 px). (Ant Design: "Tự nhiên" – giảm tải nhận thức; "Chắc chắn" – dùng thành phần nhất quán.)
- Phản hồi tức thì (Ant Design: "Có ý nghĩa"): bấm nút phải đổi trạng thái ngay (đang gửi, đã tắt tiếng...), mọi trạng thái rỗng/lỗi/mất kết nối có chữ giải thích rõ và việc cần làm.
- Vùng bấm (Google Material): mọi nút/liên kết tương tác cao tối thiểu 48 px; nút chính ở màn hình tài xế ≥ 64 px. Có focus ring rõ khi dùng bàn phím.
- Tương phản (Google Material 3): chữ ≥ 4.5:1, thành phần giao diện ≥ 3:1.
- KHÔNG chỉ dựa vào màu để báo trạng thái: mỗi trạng thái có thêm biểu tượng SVG tự vẽ (✓ / ! / ⚠, dùng inline SVG, không thư viện icon) và nhãn chữ, dùng cùng một màu cho cùng một ý nghĩa ở mọi nơi (xanh = bình thường, vàng = chú ý, đỏ = nguy hiểm).
- Hệ thống thiết kế nhất quán: định nghĩa màu và bán kính bo góc bằng biến CSS/Tailwind một chỗ, không rải màu hex khắp nơi.
- Tôn trọng prefers-reduced-motion.

## OUTPUT_START
1. Danh sách file đã tạo/sửa
2. Giải thích ngắn (tối đa 10 dòng)
3. Rủi ro / điểm chưa chắc
## OUTPUT_END
