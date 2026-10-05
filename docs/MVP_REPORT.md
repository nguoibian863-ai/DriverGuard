# Báo cáo MVP DriverGuard

Ngày: 2026-10-05 · Nhánh: `feature/mvp-core` · Người kiểm soát chất lượng: Claude

## 1. Kết luận ngắn

MVP **chạy được từ đầu đến cuối** trên máy này: camera → MediaPipe/YOLO → máy trạng thái → điểm rủi ro → backend FastAPI (REST, WebSocket, MJPEG, SQLite) → dashboard Next.js.

**Một điều chưa kiểm chứng được:** chưa có ai ngồi trước camera khi tôi chạy thử, nên phần nhận diện **khuôn mặt thật qua camera** chưa được thử. Chuỗi xử lý mặt đã được kiểm chứng trên ảnh chân dung mẫu và bằng mô phỏng. Sếp cần chạy thử một lần có mặt trước camera (mục 6).

| Hạng mục | Kết quả |
|---|---|
| Test tự động | **46/46 pass** (41 lõi AI, 5 backend) |
| Build dashboard | Thành công (Next.js 16, TypeScript) |
| Tích hợp toàn hệ thống (chế độ mô phỏng) | Đạt: WebSocket, MJPEG, REST, SQLite, giao diện đều hoạt động |
| Camera thật | Mở được, ~16 FPS; chưa thử với người thật (xem trên) |
| YOLO điện thoại trên GPU RTX 3050 | ~5 FPS, trễ ~24 ms; chưa thử với điện thoại thật |

## 2. Những gì đã làm được

**Lõi AI (`ai/`)**
- EAR, MAR (công thức landmark chuẩn).
- Neutral Pose Calibration: trung vị yaw/pitch trong 4 giây đầu, bù lệch góc camera.
- `TimedBuffer`: đo thời lượng liên tục theo thời gian thực, không phụ thuộc FPS.
- `DurationFSM`: IDLE → CANDIDATE → ACTIVE → COOLDOWN, chống báo giả một khung hình và chống spam.
- `RiskEngine`: điểm rủi ro suy hao theo hàm mũ, Acute Bypass khi nhắm mắt từ 2 giây.
- `DriverPipeline`: gom thành 6 loại sự kiện (`DROWSINESS_ACUTE`, `CHRONIC_FATIGUE`, `LOOKING_AWAY`, `LOOKING_DOWN`, `PHONE_USAGE`, `DRIVER_ABSENCE`) cộng cờ ngáp; có PERCLOS và đếm ngáp cho rủi ro mãn tính.
- Nhận diện khuôn mặt bằng MediaPipe FaceLandmarker; điện thoại bằng YOLO nano chạy luồng riêng ~5 FPS, lọc ROI để phân biệt `PHONE_VISIBLE` với `PHONE_USAGE`.
- Worker chạy tiến trình riêng, có chế độ mô phỏng không cần camera.

**Backend (`apps/backend`)**: `/api/v1/health`, `/ws/status`, `/api/v1/video/stream` (MJPEG), `calibrate`, `mute`, `events`, `config`; SQLite lưu phiên lái và sự kiện.

**Dashboard (`apps/web`)**: video trực tiếp, thanh điểm rủi ro kèm biểu ngữ NGUY HIỂM, trạng thái tài xế, đồ thị EAR/MAR, lịch sử sự kiện, nút Hiệu chuẩn và Tắt tiếng.

## 3. Ai làm gì và chất lượng

| Phần | Người làm | Kiểm chứng của Claude |
|---|---|---|
| `buffers.py`, `risk/`, `head_pose.py`, toàn bộ backend | Codex | Đọc code, chạy lại test, chạy tích hợp thật. Sửa thêm 3 lỗi (bên dưới). |
| `ear.py`, `mar.py`, `drowsiness.py` (FSM) | Gemini | Đọc code, chạy test. FSM bị lỗi sai số số thực, tôi sửa. |
| `pipeline.py`, `worker.py`, thị giác, dashboard, hợp đồng IPC | Claude | Test và chạy tích hợp. |

**Gemini không làm phần dashboard.** Lệnh giao việc cho Gemini lần đó bị hệ thống phân quyền chặn (lý do ghi: "Create Unsafe Agents"). Tôi không tìm đường vòng mà tự viết dashboard. Ở vòng trước, task EAR/MAR của Gemini phải giao 3 lần mới ra code (lần đầu nó giao lại cho subagent rồi thoát, lần hai bị chặn vì chế độ headless không chạy được lệnh).

**Các lỗi tôi tìm ra qua kiểm tra và đã sửa**
1. FSM không kích hoạt đúng biên vì sai số số thực (`2.8 − 1.0 = 1.7999…`). Thêm dung sai `1e-9`.
2. Rủi ro mãn tính báo sau vài giây vì PERCLOS tính trên cửa sổ quá ít dữ liệu. Nay cần quan sát ít nhất nửa cửa sổ 60 giây.
3. **Ngưỡng nhắm mắt cố định 0.20 sẽ báo giả** với người mắt nhỏ (ảnh mẫu có EAR mở mắt = 0.207). Nay ngưỡng = 70% EAR mở mắt của chính tài xế, lấy lúc hiệu chuẩn, kẹp 0.10–0.25.
4. MediaPipe (C++) sập vì đường dẫn thư mục có dấu tiếng Việt. Nạp mô hình từ bytes để né.
5. Tiến trình worker không thoát sau lệnh `stop` do hàng đợi còn dữ liệu. Đã sửa.
6. Backend: `camera_connected` bị phụ thuộc vào việc thấy mặt (sai); sự kiện không gắn phiên lái nào; `/config` không trả ngưỡng; backend không tự tìm được package `ai`. Đã sửa cả bốn.

## 4. Giới hạn đã biết (chưa làm hoặc chưa chắc)

- **Dấu của pitch chưa được kiểm chứng.** Quy ước góc từ ma trận MediaPipe có thể làm "cúi đầu" ra pitch âm. Đã có tham số `pitch_sign` trong `ai/config/thresholds.yaml` để đảo.
- **Ngưỡng ngáp (MAR 0.60) và ROI điện thoại là ước lượng**, chưa hiệu chỉnh bằng dữ liệu thật. ROI mới dùng vùng quanh mặt/ngực, chưa dùng ROI bàn tay.
- Chưa có: đánh giá trên dataset (NTHU-DDD, YawDD, State Farm), ONNX/TensorRT, Docker Compose, lưu snapshot (giới hạn 500 ảnh), âm thanh cảnh báo (mới có biểu ngữ trên giao diện), đồ thị FPS/latency.
- Endpoint danh sách phiên (`GET /sessions`, `/stop`) chưa làm; mỗi lần khởi động backend tạo một phiên.
- Cảnh báo thị giác chỉ có trên dashboard; nút "Tắt tiếng" mới đặt cờ `muted` (chưa có tiếng để tắt).
- Chỉ test được trên một máy (Windows 11, RTX 3050 4 GB). Một số test backend dùng chung một hàm test lớn do Codex viết.

## 5. Rủi ro

| Rủi ro | Mức | Ghi chú |
|---|---|---|
| Báo giả/bỏ sót ngoài đời thật | Cao | Chưa đo F1, độ trễ phát hiện, báo giả/phút trên dữ liệu thật (Phase 8). |
| Kính râm, thiếu sáng, đội mũ | Cao | MediaPipe mất mặt → `DRIVER_ABSENCE`. Chưa có chế độ hồng ngoại. |
| Repo GitHub đang **public** | Trung bình | Sếp cần quyết định đổi sang private hay không. |
| Đường dẫn dự án có dấu tiếng Việt | Thấp | Đã né cho MediaPipe; thư viện khác có thể gặp lỗi tương tự. |

## 6. Việc sếp cần làm để xác nhận MVP

```powershell
.\scripts\run_backend.ps1      # camera thật
.\scripts\run_web.ps1          # http://localhost:3000
```
1. Ngồi trước camera, bấm **Hiệu chuẩn tư thế**, nhìn thẳng khoảng 4 giây (huy hiệu "Đã hiệu chuẩn" bật).
2. Nhắm mắt khoảng 2 giây → phải thấy "Buồn ngủ" và điểm rủi ro lên mức NGUY HIỂM.
3. Quay đầu sang bên 2 giây → "Quay đầu lệch hướng". Cúi đầu → "Cúi đầu". Nếu cúi mà không báo, đổi `pitch_sign` thành `-1.0`.
4. Cầm điện thoại gần mặt khoảng 2 giây → "Dùng điện thoại".
5. Nếu báo giả hoặc không nhạy, gửi tôi kết quả để chỉnh `ai/config/thresholds.yaml`.

## 7. Đề xuất bước tiếp theo

1. Sếp thử với người thật (mục 6), tôi chỉnh ngưỡng theo kết quả.
2. Thêm âm thanh cảnh báo và lưu snapshot sự kiện.
3. Chạy đánh giá trên dataset công khai để có số liệu F1 và báo giả/phút.
4. ONNX Runtime và đóng gói Docker Compose.
