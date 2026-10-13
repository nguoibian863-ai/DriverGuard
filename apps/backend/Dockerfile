# Backend + AI worker. Mặc định chạy chế độ mô phỏng (không cần camera);
# để dùng camera thật, bỏ DRIVERGUARD_SIMULATE và cấp thiết bị /dev/video0.
FROM python:3.12-slim

# libGL/libglib: OpenCV cần; libgomp1: onnxruntime/torch cần
RUN apt-get update && apt-get install -y --no-install-recommends \
        libgl1 libglib2.0-0 libgomp1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Bộ thư viện tối thiểu để chạy backend + worker mô phỏng.
# Chế độ camera thật cần thêm mediapipe, ultralytics, torch (xem requirements.txt).
RUN pip install --no-cache-dir \
        fastapi uvicorn[standard] pydantic websockets \
        numpy pyyaml opencv-python-headless

COPY ai/ /app/ai/
COPY apps/backend/ /app/backend/

ENV PYTHONPATH=/app:/app/backend \
    DRIVERGUARD_DB=/data/driverguard.db \
    DRIVERGUARD_SIMULATE=1
VOLUME ["/data"]
EXPOSE 8000

WORKDIR /app/backend
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
