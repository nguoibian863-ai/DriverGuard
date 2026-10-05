# Bộ nhớ công việc

Đọc tệp này cùng `AGENTS.md` trước mỗi nhiệm vụ. Ghi lại kết quả đã hoàn thành và việc còn tồn đọng để tránh làm lại hoặc bỏ sót.

## 2026-10-05
- UI-004: Đã đổi giao diện /monitor sang khung phẳng và token màu có fallback, bỏ nền navy/pill, chuẩn hóa bảng sự kiện, biểu đồ, thanh rủi ro và nút; giữ logic và drawer. `npm run lint` và `npx tsc --noEmit` đạt; 17/17 test đạt khi chạy `node --test --test-isolation=none lib/*.test.ts`. `npm run build` biên dịch đạt nhưng dừng TypeScript do `spawn EPERM`; `npm test` cũng bị `spawn EPERM` ở test runner mặc định.
- Hoàn thiện backend MVP: SQLite sessions/events, bridge telemetry/frame, WebSocket, REST, MJPEG, lifespan worker và CORS. Test backend chạy 1 passed (DRIVERGUARD_START_WORKER=0). `ai/runtime/worker.py` hiện rỗng nên chưa kiểm chứng chế độ chạy worker thật.
- Chốt vai trò: user là chỉ huy tối cao và quyết định cuối cùng; Claude điều phối, giao việc và kiểm tra; Codex thực thi.
- Nếu quyết định của user và Claude khác nhau, hỏi user để chốt phần có xung đột.
- Chưa có nhiệm vụ triển khai tài liệu hoặc mã nguồn nào trong lượt này.
- UI-002: Đã tạo route /monitor, timeline 5 phút, bảng sự kiện với drawer và bảng sức khỏe hệ thống. Test timeline 3/3 và lint phần /monitor đạt. Lint toàn web còn lỗi ở components/driver của UI-001; build bị spawn EPERM tại bước TypeScript; npm test với script hiện tại (node --test lib/) bị lỗi môi trường/Node khi chạy thư mục.
- UI-003: Đã thiết kế lại giao diện chế độ Tài xế theo `docs/ui-design-spec.md` (v2 - bỏ "mùi AI"): chuyển sang Inter (latin + vietnamese), khai báo đủ token màu sáng/tối trong `globals.css`, gỡ toàn bộ glow/gradient/pill/rounded-full/font-bold, viết lại StartGate, StatusScreen và CalibrationRing theo chuẩn HMI ô tô (nền đặc theo mức, tam giác SVG 4px trong DANGER, nút chữ nhật ≥64px và ≥48px), giữ nguyên 100% logic và API calls.

