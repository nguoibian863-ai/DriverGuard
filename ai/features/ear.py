import numpy as np


def eye_aspect_ratio(eye: np.ndarray) -> float:
    """Tính tỉ lệ khung hình mắt (Eye Aspect Ratio - EAR).

    Tham số:
        eye (np.ndarray): Mảng numpy kích thước (6, 2) chứa tọa độ 6 điểm mốc p1..p6.

    Trả về:
        float: Giá trị EAR. Trả về 0.0 nếu mẫu số bằng 0.
    """
    eye = np.asarray(eye, dtype=float)
    dist_v1 = np.linalg.norm(eye[1] - eye[5])
    dist_v2 = np.linalg.norm(eye[2] - eye[4])
    dist_h = np.linalg.norm(eye[0] - eye[3])

    denom = 2.0 * dist_h
    if denom == 0.0:
        return 0.0

    return float((dist_v1 + dist_v2) / denom)
