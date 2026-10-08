# Tóm tắt dự án (cập nhật 2026-10-05)

## Kiến trúc hiện tại
Python 3.11: MediaPipe (mặt/EAR/MAR/góc đầu) + YOLO26x (điện thoại) -> máy trạng thái thời gian -> RiskEngine (suy hao, acute bypass) -> FastAPI (REST, WebSocket, MJPEG, SQLite) -> Next.js 16 dashboard. Worker AI chạy tiến trình riêng. Hợp đồng IPC: docs/mvp-contract.md.

## Phase hiện tại
MVP chạy được đầu-cuối trên feature/mvp-core. UI hai chế độ: Tài xế (/) và Giám sát (/monitor).

## Rủi ro đang mở
- Chưa thử với người thật trước camera (EAR/MAR/góc đầu, dấu pitch).
- Ngưỡng ngáp và ROI điện thoại chưa hiệu chỉnh; ROI phụ thuộc mặt (đã thêm giữ hộp mặt 2 giây, chưa kiểm chứng).
- Chưa đánh giá trên NTHU-DDD / YawDD.

## Quyết định gần nhất
- 2026-10-05 — YOLO điện thoại mặc định yolo26x, imgsz 640, conf 0,25 (F1 0,88 trên State Farm) (decisions.md)
- 2026-10-05 — UI đơn giản; 2 chế độ; cảnh báo leo thang theo thời gian (decisions.md)
- Figma: https://www.figma.com/design/wSNIVVu52YnG0VXp7JVUGJ (4 màn hình)
