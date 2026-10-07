"""Phát hiện pose COCO-17 bằng YOLO và tính tín hiệu hướng đầu tương đối."""

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

import numpy as np

MODELS_DIR = Path(__file__).resolve().parents[2] / "models"
_model_name = os.getenv("DRIVERGUARD_POSE_MODEL", "yolo26m-pose.pt")
_model_path = Path(_model_name)
WEIGHTS = _model_path if _model_path.is_absolute() else MODELS_DIR / _model_path

Keypoint = tuple[float, float, float]
PoseFeatures = tuple[float, float, float]


@dataclass
class PoseObservation:
    """Keypoint COCO-17 và các đặc trưng; observed_at dùng để lọc pose cũ."""

    keypoints: tuple[Keypoint, ...]
    yaw_proxy: float
    pitch_proxy: float
    ear_asym: float
    observed_at: float | None = None


def compute_pose_features(keypoints: Sequence[Sequence[float]]) -> PoseFeatures | None:
    """Tính yaw/pitch proxy và bất đối xứng tai; không phụ thuộc YOLO."""
    if len(keypoints) < 17:
        return None
    try:
        nose = keypoints[0]
        left_ear, right_ear = keypoints[3], keypoints[4]
        left_shoulder, right_shoulder = keypoints[5], keypoints[6]
        required = (nose, left_shoulder, right_shoulder)
        if any(len(point) < 3 or float(point[2]) < 0.3 for point in required):
            return None

        shoulder_width = abs(float(right_shoulder[0]) - float(left_shoulder[0]))
        if shoulder_width <= 0:
            return None
        shoulder_mid_x = (float(left_shoulder[0]) + float(right_shoulder[0])) / 2
        shoulder_mid_y = (float(left_shoulder[1]) + float(right_shoulder[1])) / 2
        yaw_proxy = (float(nose[0]) - shoulder_mid_x) / shoulder_width
        pitch_proxy = (float(nose[1]) - shoulder_mid_y) / shoulder_width
        ear_asym = float(left_ear[2]) - float(right_ear[2])
    except (IndexError, TypeError, ValueError):
        return None
    return yaw_proxy, pitch_proxy, ear_asym


class PoseTracker:
    """YOLO26 pose; tải model vào ``models/`` và tự dùng GPU nếu có."""

    def __init__(self, weights: Path = WEIGHTS, conf: float = 0.25, imgsz: int = 640) -> None:
        import torch
        from ultralytics import YOLO

        self.device = 0 if torch.cuda.is_available() else "cpu"
        self.conf = conf
        self.imgsz = imgsz
        weights.parent.mkdir(parents=True, exist_ok=True)
        if not weights.exists():
            from ultralytics.utils.downloads import attempt_download_asset

            attempt_download_asset(str(weights))
        self.model = YOLO(str(weights))

    def detect(self, frame_bgr: np.ndarray) -> PoseObservation | None:
        results = self.model.predict(
            frame_bgr,
            conf=self.conf,
            device=self.device,
            verbose=False,
            imgsz=self.imgsz,
        )
        best: tuple[float, np.ndarray] | None = None
        for result in results:
            if result.boxes is None or result.keypoints is None:
                continue
            boxes = result.boxes.xyxy.cpu().numpy()
            points = result.keypoints.data.cpu().numpy()
            for index in range(min(len(boxes), len(points))):
                x1, y1, x2, y2 = boxes[index]
                area = max(0.0, float(x2 - x1)) * max(0.0, float(y2 - y1))
                if best is None or area > best[0]:
                    best = area, points[index]

        if best is None:
            return None
        keypoints: tuple[Keypoint, ...] = tuple(
            (float(point[0]), float(point[1]), float(point[2]))
            for point in best[1]
            if len(point) >= 3
        )
        features = compute_pose_features(keypoints)
        if features is None or len(keypoints) != 17:
            return None
        return PoseObservation(keypoints, *features)
