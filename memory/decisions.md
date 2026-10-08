# Quyết định kỹ thuật

Chưa có quyết định.

## 2026-10-05 — Hướng UI/UX
- Quyết định: UI đơn giản, dễ dùng; tham khảo Google Material 3 (vùng bấm 48 px, tương phản, không chỉ dựa vào màu) và Alibaba Ant Design (Tự nhiên / Chắc chắn / Có ý nghĩa). Chưa xác minh được tài liệu chính thức của Amazon Cloudscape.
- Hai chế độ: Tài xế (`/`, tối giản, âm thanh leo thang) và Giám sát (`/monitor`). Gemini làm Tài xế (UI-001), Codex làm Giám sát (UI-002).
- Cảnh báo leo thang theo thời gian (AAA Foundation, Euro NCAP 2026).

## 2026-10-05 — Model điện thoại
- Quyết định: yolo26x, imgsz 640, conf 0,25. Lý do: State Farm F1 0,88 (Recall 0,90); yolo26n chỉ Recall 0,15 trong xe. Chi tiết: docs/EXPERIMENT_LOG.md.
- Trạng thái: áp dụng; thiết bị yếu dùng yolo26m/s qua DRIVERGUARD_YOLO_MODEL.

## 2026-10-05 — Hiệu chuẩn
- Quyết định: backend tự hiệu chuẩn khi thấy mặt lần đầu; UI chỉ hiển thị vòng đếm, không tự gọi calibrate (tránh vòng lặp đặt lại). Nút "Hiệu chuẩn lại" do người dùng bấm.

## 2026-10-05 — UI v2 (bỏ "mùi AI")
- Quyết định: giao diện thực dụng kiểu HMI ô tô + bảng vận hành; không glow/gradient/pill/hero icon/câu quảng cáo; Inter có subset tiếng Việt; token màu sáng/tối một chỗ; trạng thái bình thường yên tĩnh, WARNING nền vàng, DANGER nền đỏ đặc. Đặc tả: docs/ui-design-spec.md.
- Figma: file https://www.figma.com/design/wSNIVVu52YnG0VXp7JVUGJ chứa bản UI v1 (đã nối prototype) và một số bản chụp UI v2 chưa dọn; gói Starter đã hết hạn mức gọi công cụ MCP.

## 2026-10-05 — Ngưỡng MAR
- Quyết định: mar_threshold 0,60 -> 0,50. Lý do: thí nghiệm 4 (800 ảnh AI sinh): ngưỡng 0,60 chỉ Recall 0,675 (tính cả mất mặt 0,618); 0,50 cho F1 0,906, báo giả 2%. Không chọn 0,36 (tối ưu F1) vì dữ liệu âm quá dễ.
- Trạng thái: áp dụng; cần kiểm chứng trên người thật (nói chuyện, cười).

## 2026-10-05 — Sửa logic theo phiên thử người thật (AI-001)
- mar_threshold 0,50 -> 0,40; hệ số ngưỡng mắt 0,7 -> 0,55 kẹp [0,10; 0,20]; dự phòng 0,15; không tính nhắm mắt khi cúi đầu/ngáp; mất mặt sau quay đầu lớn = LOOKING_AWAY.
- Lý do và kiểm chứng: docs/EXPERIMENT_LOG.md mục 11–12. Hạn chế: n = 1, kiểm chứng trên cùng dữ liệu.
