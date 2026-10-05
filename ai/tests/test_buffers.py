"""Kiểm tra thời lượng tín hiệu trong TimedBuffer."""

import pytest

from ai.temporal.buffers import TimedBuffer


def test_low_ear_continuous_for_1_8_seconds() -> None:
    buffer = TimedBuffer(max_age_s=3.0)
    for timestamp in (0.0, 0.4, 1.1, 1.8):
        buffer.push(timestamp, 0.18)

    assert buffer.duration_below(0.2) >= 1.8
    assert buffer.duration_above(0.2) == 0.0


def test_interruption_resets_consecutive_duration() -> None:
    buffer = TimedBuffer(max_age_s=5.0)
    buffer.push(0.0, 0.1)
    buffer.push(1.0, 0.1)
    buffer.push(1.2, 0.3)
    buffer.push(1.5, 0.1)
    buffer.push(2.0, 0.1)

    assert buffer.duration_below(0.2) == pytest.approx(0.5)
    assert buffer.duration_above(0.2) == 0.0


def test_above_threshold_and_strict_comparison() -> None:
    buffer = TimedBuffer(max_age_s=5.0)
    buffer.push(0.0, 0.5)
    buffer.push(1.0, 0.5)
    assert buffer.duration_above(0.4) == 1.0

    buffer.push(1.5, 0.4)
    assert buffer.duration_above(0.4) == 0.0
    assert buffer.duration_below(0.4) == 0.0


def test_max_age_limits_duration_and_reset_clears_samples() -> None:
    buffer = TimedBuffer(max_age_s=1.0)
    buffer.push(0.0, 0.1)
    buffer.push(1.0, 0.1)
    buffer.push(2.0, 0.1)
    assert buffer.duration_below(0.2) == 1.0

    buffer.reset()
    assert buffer.duration_below(0.2) == 0.0
    buffer.push(3.0, 0.1)
    assert buffer.duration_below(0.2) == 0.0


def test_invalid_age_and_out_of_order_timestamp() -> None:
    with pytest.raises(ValueError):
        TimedBuffer(max_age_s=0.0)

    buffer = TimedBuffer(max_age_s=1.0)
    buffer.push(2.0, 0.1)
    with pytest.raises(ValueError):
        buffer.push(1.0, 0.1)
