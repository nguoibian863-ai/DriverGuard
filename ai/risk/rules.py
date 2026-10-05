"""Quy tắc phân loại mức rủi ro."""

from enum import Enum


class RiskLevel(Enum):
    """Ba mức rủi ro."""

    SAFE = "SAFE"
    WARNING = "WARNING"
    DANGER = "DANGER"


def level_from_score(score: float) -> RiskLevel:
    """Phân loại điểm theo các ngưỡng 40 và 70."""
    if score < 40:
        return RiskLevel.SAFE
    if score < 70:
        return RiskLevel.WARNING
    return RiskLevel.DANGER
