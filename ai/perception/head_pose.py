"""Hiệu chuẩn góc đầu tương đối so với tư thế ban đầu."""

from statistics import median


class NeutralPoseCalibrator:
    """Lấy trung vị yaw và pitch trong cửa sổ đầu phiên."""

    def __init__(self, window_s: float = 4.0) -> None:
        if window_s <= 0:
            raise ValueError("window_s phải lớn hơn 0")
        self.window_s = window_s
        self.is_calibrated = False
        self.yaw0: float | None = None
        self.pitch0: float | None = None
        self._start: float | None = None
        self._yaw_samples: list[float] = []
        self._pitch_samples: list[float] = []

    def add_sample(self, timestamp: float, yaw: float, pitch: float) -> None:
        """Thu mẫu trong cửa sổ và chốt hiệu chuẩn khi cửa sổ kết thúc."""
        if self.is_calibrated:
            return
        if self._start is None:
            self._start = timestamp
        if timestamp < self._start + self.window_s:
            self._yaw_samples.append(yaw)
            self._pitch_samples.append(pitch)
            return
        self.yaw0 = median(self._yaw_samples)
        self.pitch0 = median(self._pitch_samples)
        self.is_calibrated = True

    def relative(self, yaw: float, pitch: float) -> tuple[float, float]:
        """Trả góc lệch so với trung vị tư thế chuẩn."""
        if not self.is_calibrated or self.yaw0 is None or self.pitch0 is None:
            raise RuntimeError("Chưa hiệu chuẩn tư thế chuẩn")
        return yaw - self.yaw0, pitch - self.pitch0


def classify_head(
    rel_yaw: float,
    rel_pitch: float,
    yaw_thr: float = 30.0,
    pitch_thr: float = 20.0,
) -> str:
    """Phân loại hướng đầu, ưu tiên trạng thái nhìn lệch."""
    if abs(rel_yaw) > yaw_thr:
        return "LOOKING_AWAY"
    if rel_pitch > pitch_thr:
        return "LOOKING_DOWN"
    return "FORWARD"
