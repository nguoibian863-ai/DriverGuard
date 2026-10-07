# Vấn đề tồn đọng (cập nhật 2026-10-06)

- Kiểm chứng AI-001 mới chỉ bằng phát lại chính dữ liệu đã dùng để chỉnh tham số; n = 1 người (docs/EXPERIMENT_LOG.md mục 12.3).
- Quay trái chưa được phát hiện: góc 27–33° so với ngưỡng 30°.
- Điện thoại chưa kết luận: YOLO thấy 5/54 bản tin, chưa biết điện thoại có trong khung hình; phát lại không có thông tin ROI.
- FPS camera laptop trung vị 15, chưa đạt mục tiêu UR-15 ≥ 20.
- `CHRONIC_FATIGUE` xuất hiện giữa phiên do kịch bản nhắm mắt nhiều lần; chưa đánh giá trên lái xe thực.
- `npm run build` và `npm test` bị `spawn EPERM` trong môi trường này; dùng `node --test --test-isolation=none lib/*.test.ts`.
- Chế độ chạy worker thật (camera + hiệu chuẩn qua `/api/v1/sessions/calibrate`) mới được xác nhận bằng đọc mã (`ai/runtime/worker.py:67`), chưa chạy thực tế sau EXP-006.
- Gemini headless không chạy được lệnh shell; Codex: dùng `codex exec --sandbox workspace-write` (bản hiện tại không có `--full-auto`); cần rule `Bash(codex exec:*)` trong quyền.
