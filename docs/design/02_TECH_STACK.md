# Tech Stack

## 1. Nguyên tắc chọn công nghệ

Tech stack ưu tiên:

- Dễ phát triển cho một người.
- Có cộng đồng lớn.
- Phù hợp Computer Vision realtime.
- Có đường tối ưu sang edge.
- Không đưa hạ tầng phức tạp vào MVP quá sớm.

---

# 2. AI / Computer Vision

## Python

**Phiên bản đề xuất:** Python 3.11

Vai trò:

- Inference.
- Computer Vision.
- Feature extraction.
- Temporal analysis.
- Model evaluation.

## PyTorch

Dùng cho:

- Model development.
- Fine-tuning.
- Experiment.
- Export model.

## Ultralytics YOLO

Dùng cho:

- Phone detection.
- Có thể mở rộng sang face/person/object detection.

Ưu tiên model nhỏ ở MVP:

- YOLO nano.
- YOLO small nếu phần cứng cho phép.

## MediaPipe

Dùng cho:

- Face landmark.
- Eye landmarks.
- Mouth landmarks.
- Head/face geometry.

Lợi thế:

- Nhẹ.
- Realtime.
- Không cần train từ đầu.

## OpenCV

Dùng cho:

- Camera capture.
- Frame resize.
- Drawing overlays.
- Image processing.
- Video I/O.
- FPS measurement.

## NumPy

Dùng cho:

- Vector/matrix operations.
- EAR/MAR.
- Head pose calculations.
- Temporal statistics.

---

# 3. AI Runtime / Edge

## MVP

```text
PyTorch / ONNX Runtime
```

## Optimization phase

```text
PyTorch
   ↓
ONNX
   ↓
ONNX Runtime
   ↓
TensorRT (optional)
```

TensorRT chỉ nên làm sau khi pipeline đã đúng.

---

# 4. Backend

## FastAPI

Vai trò:

- REST API.
- Camera/pipeline control.
- Event API.
- Config API.
- Health check.

## WebSocket

Dùng cho realtime:

- Driver status.
- Risk score.
- FPS.
- Event notification.

## Pydantic

Dùng cho:

- API schema.
- Validation.
- Config schema.

---

# 5. Frontend

## Next.js

Dùng để xây dashboard.

## TypeScript

Tăng an toàn kiểu dữ liệu.

## Tailwind CSS

Dùng để phát triển UI nhanh.

## shadcn/ui

Dùng cho:

- Card.
- Dialog.
- Table.
- Badge.
- Alert.
- Tabs.

## Recharts

Dùng cho:

- Risk score history.
- Event frequency.
- FPS/latency chart.

---

# 6. Database

## SQLite — MVP

Lưu:

- Session.
- Event.
- Config.
- Metrics.

Lợi thế:

- Không cần cài server database.
- Phù hợp local-first.

## PostgreSQL — Phase sau

Chỉ chuyển sang PostgreSQL khi cần:

- Nhiều người dùng.
- Nhiều edge device.
- Centralized dashboard.
- Fleet scale.

---

# 7. Testing

## pytest

Unit/integration tests cho backend và AI logic.

## Playwright

E2E test cho frontend nếu cần.

---

# 8. Development Tools

- Git.
- GitHub.
- VS Code.
- Ruff.
- Black.
- mypy — optional.
- ESLint.
- Prettier.

---

# 9. MLOps — optional

## MLflow

Theo dõi:

- Model version.
- Experiment.
- Metrics.
- Parameters.

Không bắt buộc cho MVP.

---

# 10. Tech Stack tổng hợp

```text
Frontend
Next.js
TypeScript
Tailwind CSS
shadcn/ui
Recharts

        │ HTTP / WebSocket
        ▼

Backend
FastAPI
Pydantic
SQLite

        │
        ▼

AI Runtime
Python
PyTorch
OpenCV
MediaPipe
YOLO
NumPy

        │
        ▼

Optimization
ONNX Runtime
TensorRT (later)
```
