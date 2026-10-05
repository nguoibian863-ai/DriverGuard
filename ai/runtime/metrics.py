"""Đo FPS theo cửa sổ trượt 1 giây."""

from collections import deque


class FpsCounter:
    """Đếm số lần tick trong 1 giây gần nhất."""

    def __init__(self, window_s: float = 1.0) -> None:
        self.window_s = window_s
        self._ticks: deque[float] = deque()

    def tick(self, now: float) -> None:
        self._ticks.append(now)
        self._prune(now)

    def _prune(self, now: float) -> None:
        while self._ticks and self._ticks[0] < now - self.window_s:
            self._ticks.popleft()

    def value(self, now: float) -> int:
        self._prune(now)
        return round(len(self._ticks) / self.window_s)
