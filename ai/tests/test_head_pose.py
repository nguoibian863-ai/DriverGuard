"""Kiểm tra hiệu chuẩn và phân loại hướng đầu."""

import pytest

from ai.perception.head_pose import NeutralPoseCalibrator, classify_head


def test_median_ignores_outlier_and_window_end() -> None:
    calibrator = NeutralPoseCalibrator(window_s=4.0)
    for timestamp, yaw, pitch in [
        (10.0, 12.0, -4.0),
        (11.0, 13.0, -3.0),
        (12.0, 150.0, 90.0),
        (13.0, 11.0, -5.0),
    ]:
        calibrator.add_sample(timestamp, yaw, pitch)
    assert not calibrator.is_calibrated

    calibrator.add_sample(14.0, -100.0, -100.0)
    assert calibrator.is_calibrated
    assert calibrator.yaw0 == 12.5
    assert calibrator.pitch0 == -3.5

    calibrator.add_sample(15.0, 999.0, 999.0)
    assert calibrator.yaw0 == 12.5
    assert calibrator.pitch0 == -3.5


def test_camera_offset_is_removed_for_forward_pose() -> None:
    calibrator = NeutralPoseCalibrator()
    calibrator.add_sample(0.0, 18.0, -7.0)
    calibrator.add_sample(1.0, 19.0, -6.0)
    calibrator.add_sample(2.0, 17.0, -8.0)
    calibrator.add_sample(4.0, 18.0, -7.0)
    assert calibrator.relative(18.0, -7.0) == pytest.approx((0.0, 0.0))


def test_relative_before_calibration_raises() -> None:
    calibrator = NeutralPoseCalibrator()
    calibrator.add_sample(0.0, 0.0, 0.0)
    with pytest.raises(RuntimeError):
        calibrator.relative(0.0, 0.0)


@pytest.mark.parametrize(
    ("yaw", "pitch", "expected"),
    [
        (31.0, 25.0, "LOOKING_AWAY"),
        (-31.0, 0.0, "LOOKING_AWAY"),
        (0.0, 21.0, "LOOKING_DOWN"),
        (30.0, 20.0, "FORWARD"),
        (0.0, -25.0, "FORWARD"),
    ],
)
def test_classify_head(yaw: float, pitch: float, expected: str) -> None:
    assert classify_head(yaw, pitch) == expected
