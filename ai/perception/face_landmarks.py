"""MediaPipe FaceLandmarker -> EAR, MAR, góc đầu."""

import math
from pathlib import Path

import mediapipe as mp
import numpy as np
from mediapipe.tasks.python import BaseOptions, vision

from ai.features.ear import eye_aspect_ratio
from ai.features.mar import mouth_aspect_ratio
from ai.runtime.pipeline import FaceObservation

MODEL_PATH = Path(__file__).resolve().parents[2] / "models" / "mediapipe" / "face_landmarker.task"

# Thứ tự p1..p6 chuẩn (góc ngoài, trên, trên, góc trong, dưới, dưới)
RIGHT_EYE = [33, 160, 158, 133, 153, 144]
LEFT_EYE = [362, 385, 387, 263, 373, 380]
# 0=khóe trái, 1..3 môi trên, 4=khóe phải, 5..7 môi dưới (đối xứng 3,2,1)
MOUTH = [61, 81, 13, 311, 291, 402, 14, 178]


def euler_from_matrix(m: np.ndarray) -> tuple[float, float, float]:
    """Ma trận biến đổi 4x4 -> (yaw, pitch, roll) bằng độ."""
    r = m[:3, :3]
    sy = math.hypot(r[0, 0], r[1, 0])
    pitch = math.degrees(math.atan2(r[2, 1], r[2, 2]))
    yaw = math.degrees(math.atan2(-r[2, 0], sy))
    roll = math.degrees(math.atan2(r[1, 0], r[0, 0]))
    return yaw, pitch, roll


class FaceLandmarkTracker:
    """Bọc FaceLandmarker (chế độ VIDEO) trả về FaceObservation và bbox khuôn mặt."""

    def __init__(self, model_path: Path = MODEL_PATH) -> None:
        options = vision.FaceLandmarkerOptions(
            # Nạp từ bytes: tránh lỗi native của MediaPipe với đường dẫn có dấu tiếng Việt
            base_options=BaseOptions(model_asset_buffer=Path(model_path).read_bytes()),
            running_mode=vision.RunningMode.VIDEO,
            num_faces=1,
            output_facial_transformation_matrixes=True,
        )
        self._landmarker = vision.FaceLandmarker.create_from_options(options)
        self._last_ms = -1

    def process(
        self, rgb: np.ndarray, timestamp_s: float
    ) -> tuple[FaceObservation | None, tuple[int, int, int, int] | None, np.ndarray | None]:
        """Trả (quan sát, bbox khuôn mặt x1,y1,x2,y2, mảng landmark pixel)."""
        ts_ms = max(int(timestamp_s * 1000), self._last_ms + 1)
        self._last_ms = ts_ms
        image = mp.Image(image_format=mp.ImageFormat.SRGB, data=np.ascontiguousarray(rgb))
        result = self._landmarker.detect_for_video(image, ts_ms)
        if not result.face_landmarks:
            return None, None, None
        h, w = rgb.shape[:2]
        pts = np.array([[lm.x * w, lm.y * h] for lm in result.face_landmarks[0]])
        ear = (eye_aspect_ratio(pts[RIGHT_EYE]) + eye_aspect_ratio(pts[LEFT_EYE])) / 2.0
        mar = mouth_aspect_ratio(pts[MOUTH])
        if result.facial_transformation_matrixes:
            yaw, pitch, roll = euler_from_matrix(np.array(result.facial_transformation_matrixes[0]))
        else:
            yaw = pitch = roll = 0.0
        x1, y1 = pts.min(axis=0)
        x2, y2 = pts.max(axis=0)
        obs = FaceObservation(ear=ear, mar=mar, yaw=yaw, pitch=pitch, roll=roll)
        return obs, (int(x1), int(y1), int(x2), int(y2)), pts

    def close(self) -> None:
        self._landmarker.close()
