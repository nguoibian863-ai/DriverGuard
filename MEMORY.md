# Bộ nhớ công việc

Đọc tệp này cùng `AGENTS.md` trước mỗi nhiệm vụ. Ghi lại kết quả đã hoàn thành và việc còn tồn đọng để tránh làm lại hoặc bỏ sót.

## 2026-10-05
- Hoàn thiện backend MVP: SQLite sessions/events, bridge telemetry/frame, WebSocket, REST, MJPEG, lifespan worker và CORS. Test backend chạy 1 passed (DRIVERGUARD_START_WORKER=0). `ai/runtime/worker.py` hiện rỗng nên chưa kiểm chứng chế độ chạy worker thật.
- Chốt vai trò: user là chỉ huy tối cao và quyết định cuối cùng; Claude điều phối, giao việc và kiểm tra; Codex thực thi.
- Nếu quyết định của user và Claude khác nhau, hỏi user để chốt phần có xung đột.
- Chưa có nhiệm vụ triển khai tài liệu hoặc mã nguồn nào trong lượt này.
- UI-002: Đã tạo route /monitor, timeline 5 phút, bảng sự kiện với drawer và bảng sức khỏe hệ thống. Test timeline 3/3 và lint phần /monitor đạt. Lint toàn web còn lỗi ở components/driver của UI-001; build bị spawn EPERM tại bước TypeScript; npm test với script hiện tại (node --test lib/) bị lỗi môi trường/Node khi chạy thư mục.
