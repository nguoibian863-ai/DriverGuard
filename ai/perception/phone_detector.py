"""Phát hiện điện thoại bằng YOLO nano + lọc ROI không gian (PHONE_VISIBLE vs PHONE_USAGE)."""

import os
from pathlib import Path

import numpy as np

PHONE_CLASS_ID = 67  # 'cell phone' trong COCO
MODELS_DIR = Path(__file__).resolve().parents[2] / "models"
# Đổi model bằng biến môi trường, ví dụ DRIVERGUARD_YOLO_MODEL=yolo26n.pt
WEIGHTS = MODELS_DIR / os.getenv("DRIVERGUARD_YOLO_MODEL", "yolo26x.pt")

Box = tuple[int, int, int, int]


def is_usage_region(phone: Box, face: Box | None) -> bool:
    """Điện thoại nằm gần mặt/ngực tài xế: tâm phone nằm trong vùng mặt mở rộng.

    Vùng: ngang ±1.5 chiều rộng mặt quanh tâm mặt, từ 0.5 chiều cao mặt phía trên
    đến 3 chiều cao mặt phía dưới (vùng ngực/tay). Phone gắn taplo (xa mặt) không tính.
    """
    if face is None:
        return False
    fx1, fy1, fx2, fy2 = face
    fw, fh = max(fx2 - fx1, 1), max(fy2 - fy1, 1)
    cx, cy = (phone[0] + phone[2]) / 2, (phone[1] + phone[3]) / 2
    face_cx = (fx1 + fx2) / 2
    return abs(cx - face_cx) <= 1.5 * fw and fy1 - 0.5 * fh <= cy <= fy2 + 3.0 * fh


class FaceBoxHold:
    """Giữ hộp mặt cuối cùng trong hold_s giây.

    Khi tay che mặt lúc gọi điện thoại, MediaPipe mất mặt; vẫn cần vùng mặt để lọc ROI điện thoại.
    """

    def __init__(self, hold_s: float = 2.0) -> None:
        self.hold_s = hold_s
        self._box: Box | None = None
        self._time = -1e9

    def update(self, now: float, box: Box | None) -> Box | None:
        if box is not None:
            self._box, self._time = box, now
            return box
        return self._box if now - self._time <= self.hold_s else None


class PhoneDetector:
    """YOLO nano; tự dùng GPU nếu có."""

    def __init__(self, weights: Path = WEIGHTS, conf: float = 0.25) -> None:
        import torch
        from ultralytics import YOLO

        self.device = 0 if torch.cuda.is_available() else "cpu"
        self.conf = conf
        weights.parent.mkdir(parents=True, exist_ok=True)
        if not weights.exists():
            # Tải đúng vào models/ (không rải file .pt ra thư mục đang chạy)
            from ultralytics.utils.downloads import attempt_download_asset

            attempt_download_asset(str(weights))
        self.model = YOLO(str(weights))

    def detect(self, bgr: np.ndarray) -> list[Box]:
        results = self.model.predict(
            bgr, classes=[PHONE_CLASS_ID], conf=self.conf, device=self.device, verbose=False, imgsz=640
        )
        boxes: list[Box] = []
        for r in results:
            for b in r.boxes.xyxy.cpu().numpy():
                boxes.append((int(b[0]), int(b[1]), int(b[2]), int(b[3])))
        return boxes
