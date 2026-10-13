# DriverGuard (MVP)

Hệ thống giám sát tài xế bằng Computer Vision: phát hiện buồn ngủ, ngáp, mất tập trung,
dùng điện thoại và tính điểm rủi ro theo thời gian thực. Tài liệu thiết kế: `docs/design/`.
Báo cáo MVP: `docs/MVP_REPORT.md`.

## Cài môi trường
```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
# GPU NVIDIA (tùy chọn):
.\.venv\Scripts\python.exe -m pip install --force-reinstall --no-deps torch torchvision --index-url https://download.pytorch.org/whl/cu128
cd apps\web; npm install
```
Mô hình: `models/mediapipe/face_landmarker.task` (tải từ
`https://storage.googleapis.com/mediapipe-models/face_landmarker/face_landmarker/float16/1/face_landmarker.task`);
`models/yolo11n.pt` tự tải lần chạy đầu.

## Chạy
```powershell
.\scripts\run_backend.ps1            # camera thật; thêm -Simulate để chạy không cần camera
.\scripts\run_web.ps1                # mở http://localhost:3000
```

## Kiểm thử
```powershell
.\.venv\Scripts\python.exe -m pytest ai -q                 # từ thư mục gốc
cd apps\backend; ..\..\.venv\Scripts\python.exe -m pytest tests -q
cd apps\web; npm test; npm run lint; npm run build
```

Lưu ý: không đặt dự án ở đường dẫn có dấu tiếng Việt nếu có thể; MediaPipe (C++) từng lỗi với
đường dẫn như vậy (đã né bằng cách nạp mô hình từ bytes).

## Chạy bằng Docker (chế độ mô phỏng, không cần camera)
```bash
docker compose up --build     # web http://localhost:3000, API http://localhost:8000
```
Lưu ý: compose đã được kiểm cú pháp nhưng **chưa build thử image**.

## Kiểm thử đầu-cuối (không cần camera)
```bash
python -m pytest tests/integration -q     # chạy uvicorn thật + AI worker mô phỏng
```

CI: `.github/workflows/ci.yml` chạy test Python, e2e, lint, tsc, test và build web trên mỗi PR.
Trạng thái dự án và việc còn lại: `docs/MVP_REPORT.md` mục 8.
