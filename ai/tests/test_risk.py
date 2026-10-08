"""Kiểm thử Dual Risk Engine."""

from math import exp

import pytest

from ai.risk.engine import RiskEngine, RiskState
from ai.risk.rules import RiskLevel, level_from_score


def test_level_thresholds() -> None:
    assert level_from_score(39.9) is RiskLevel.SAFE
    assert level_from_score(40) is RiskLevel.WARNING
    assert level_from_score(69.9) is RiskLevel.WARNING
    assert level_from_score(70) is RiskLevel.DANGER


def test_exponential_decay() -> None:
    engine = RiskEngine()
    first = engine.update(10.0, 80.0)
    second = engine.update(11.0, 0.0)
    third = engine.update(12.0, 0.0)

    assert isinstance(first, RiskState)
    assert first.score == 80.0
    assert first.level is RiskLevel.DANGER
    assert first.acute is False
    assert second.score == pytest.approx(80.0 * exp(-0.3))
    assert third.score == pytest.approx(80.0 * exp(-0.6))
    assert 0.0 < third.score < second.score < first.score


def test_acute_bypass() -> None:
    engine = RiskEngine()
    ordinary = engine.update(0.0, 5.0, eyes_closed_s=1.99)
    acute = engine.update(0.1, 5.0, eyes_closed_s=2.0)

    assert ordinary.level is RiskLevel.SAFE
    assert ordinary.acute is False
    assert acute.score >= 70.0
    assert acute.level is RiskLevel.DANGER
    assert acute.acute is True


def test_score_clamped() -> None:
    engine = RiskEngine()
    assert engine.update(0.0, -20.0).score == 0.0
    assert engine.update(1.0, 120.0).score == 100.0


def test_decreasing_timestamp_raises() -> None:
    engine = RiskEngine()
    engine.update(2.0, 80.0)
    with pytest.raises(ValueError):
        engine.update(1.0, 0.0)
    assert engine.update(3.0, 0.0).score == pytest.approx(80.0 * exp(-0.3))
