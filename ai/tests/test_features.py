import sys
from pathlib import Path

import numpy as np
import pytest

root_dir = Path(__file__).resolve().parent.parent.parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

from ai.features.ear import eye_aspect_ratio
from ai.features.mar import mouth_aspect_ratio


def test_ear_open_greater_than_closed():
    open_eye = np.array([
        [0.0, 0.0],   # p1
        [2.0, 2.0],   # p2
        [4.0, 2.0],   # p3
        [6.0, 0.0],   # p4
        [4.0, -2.0],  # p5
        [2.0, -2.0],  # p6
    ])

    closed_eye = np.array([
        [0.0, 0.0],
        [2.0, 0.05],
        [4.0, 0.05],
        [6.0, 0.0],
        [4.0, -0.05],
        [2.0, -0.05],
    ])

    assert eye_aspect_ratio(open_eye) > eye_aspect_ratio(closed_eye)


def test_ear_zero_denominator():
    zero_width_eye = np.array([
        [0.0, 0.0],   # p1
        [0.0, 2.0],   # p2
        [0.0, 2.0],   # p3
        [0.0, 0.0],   # p4
        [0.0, -2.0],  # p5
        [0.0, -2.0],  # p6
    ])
    assert eye_aspect_ratio(zero_width_eye) == 0.0


def test_ear_manual_calculation():
    # |p1 - p4| = 6.0
    # |p2 - p6| = 4.0, |p3 - p5| = 4.0
    # EAR = (4.0 + 4.0) / (2 * 6.0) = 8.0 / 12.0 = 2/3
    eye = np.array([
        [0.0, 0.0],
        [2.0, 2.0],
        [4.0, 2.0],
        [6.0, 0.0],
        [4.0, -2.0],
        [2.0, -2.0],
    ])
    assert pytest.approx(8.0 / 12.0) == eye_aspect_ratio(eye)


def test_mar_open_greater_than_closed():
    open_mouth = np.array([
        [0.0, 0.0],   # 0: khóe trái
        [2.0, 3.0],   # 1: môi trên
        [4.0, 3.0],   # 2: môi trên
        [6.0, 3.0],   # 3: môi trên
        [8.0, 0.0],   # 4: khóe phải
        [6.0, -3.0],  # 5: môi dưới (đối xứng 3)
        [4.0, -3.0],  # 6: môi dưới (đối xứng 2)
        [2.0, -3.0],  # 7: môi dưới (đối xứng 1)
    ])

    closed_mouth = np.array([
        [0.0, 0.0],
        [2.0, 0.1],
        [4.0, 0.1],
        [6.0, 0.1],
        [8.0, 0.0],
        [6.0, -0.1],
        [4.0, -0.1],
        [2.0, -0.1],
    ])

    assert mouth_aspect_ratio(open_mouth) > mouth_aspect_ratio(closed_mouth)


def test_mar_zero_denominator():
    zero_width_mouth = np.array([
        [0.0, 0.0],
        [0.0, 2.0],
        [0.0, 2.0],
        [0.0, 2.0],
        [0.0, 0.0],
        [0.0, -2.0],
        [0.0, -2.0],
        [0.0, -2.0],
    ])
    assert mouth_aspect_ratio(zero_width_mouth) == 0.0


def test_mar_manual_calculation():
    # Ngang (0-4) = 8.0
    # Dọc (1-7) = 6.0, (2-6) = 6.0, (3-5) = 6.0 -> trung bình = 6.0
    # MAR = 6.0 / 8.0 = 0.75
    mouth = np.array([
        [0.0, 0.0],
        [2.0, 3.0],
        [4.0, 3.0],
        [6.0, 3.0],
        [8.0, 0.0],
        [6.0, -3.0],
        [4.0, -3.0],
        [2.0, -3.0],
    ])
    assert pytest.approx(0.75) == mouth_aspect_ratio(mouth)
