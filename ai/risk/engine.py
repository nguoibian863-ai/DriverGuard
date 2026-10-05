"""Tính rủi ro tích lũy và xử lý nguy cơ cấp tính."""

from dataclasses import dataclass
from math import exp

from ai.risk.rules import RiskLevel, level_from_score


@dataclass
class RiskState:
    """Trạng thái rủi ro sau một lần cập nhật."""

    score: float
    level: RiskLevel
    acute: bool


class RiskEngine:
    """Duy trì điểm rủi ro với suy hao theo thời gian."""

    def __init__(self, decay_lambda: float = 0.3) -> None:
        self.decay_lambda = decay_lambda
        self._score = 0.0
        self._timestamp: float | None = None

    def update(
        self, timestamp: float, instant_risk: float, eyes_closed_s: float = 0.0
    ) -> RiskState:
        """Cập nhật điểm và kích hoạt cảnh báo khi nhắm mắt đủ lâu."""
        if self._timestamp is not None and timestamp < self._timestamp:
            raise ValueError("timestamp không được giảm")

        dt = 0.0 if self._timestamp is None else timestamp - self._timestamp
        score = max(instant_risk, self._score * exp(-self.decay_lambda * dt))
        score = min(100.0, max(0.0, score))
        acute = eyes_closed_s >= 2.0
        if acute:
            score = max(70.0, score)

        self._score = score
        self._timestamp = timestamp
        return RiskState(score=score, level=level_from_score(score), acute=acute)
