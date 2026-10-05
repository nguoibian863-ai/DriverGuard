"""Lưu mẫu theo cửa sổ thời gian để đo tín hiệu liên tục."""

from collections import deque
from collections.abc import Callable


class TimedBuffer:
    """Lưu các mẫu mới nhất trong tối đa ``max_age_s`` giây."""

    def __init__(self, max_age_s: float) -> None:
        if max_age_s <= 0:
            raise ValueError("max_age_s phải lớn hơn 0")
        self.max_age_s = max_age_s
        self._samples: deque[tuple[float, float]] = deque()

    def push(self, timestamp: float, value: float) -> None:
        """Thêm mẫu và loại các mẫu nằm ngoài cửa sổ thời gian."""
        if self._samples and timestamp < self._samples[-1][0]:
            raise ValueError("timestamp phải không giảm")
        self._samples.append((timestamp, value))
        cutoff = timestamp - self.max_age_s
        while self._samples and self._samples[0][0] < cutoff:
            self._samples.popleft()

    def duration_below(self, threshold: float) -> float:
        """Trả thời lượng liên tục gần nhất có giá trị dưới ngưỡng."""
        return self._duration(lambda value: value < threshold)

    def duration_above(self, threshold: float) -> float:
        """Trả thời lượng liên tục gần nhất có giá trị trên ngưỡng."""
        return self._duration(lambda value: value > threshold)

    def reset(self) -> None:
        """Xóa toàn bộ mẫu đã lưu."""
        self._samples.clear()

    def _duration(self, matches: Callable[[float], bool]) -> float:
        if not self._samples or not matches(self._samples[-1][1]):
            return 0.0
        latest = self._samples[-1][0]
        start = latest
        for timestamp, value in reversed(self._samples):
            if not matches(value):
                break
            start = timestamp
        return latest - start
