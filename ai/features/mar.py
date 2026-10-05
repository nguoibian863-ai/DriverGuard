import numpy as np


def mouth_aspect_ratio(mouth: np.ndarray) -> float:
    """Tính tỉ lệ khung hình miệng (Mouth Aspect Ratio - MAR).

    Tham số:
        mouth (np.ndarray): Mảng numpy kích thước (8, 2) chứa tọa độ 8 điểm mốc miệng:
                            0: khóe trái, 1..3: môi trên, 4: khóe phải, 5..7: môi dưới (đối xứng 3, 2, 1).

    Trả về:
        float: Giá trị MAR. Trả về 0.0 nếu mẫu số (khoảng cách ngang) bằng 0.
    """
    mouth = np.asarray(mouth, dtype=float)
    dist_v1 = np.linalg.norm(mouth[1] - mouth[7])
    dist_v2 = np.linalg.norm(mouth[2] - mouth[6])
    dist_v3 = np.linalg.norm(mouth[3] - mouth[5])

    avg_vertical = (dist_v1 + dist_v2 + dist_v3) / 3.0
    dist_h = np.linalg.norm(mouth[0] - mouth[4])

    if dist_h == 0.0:
        return 0.0

    return float(avg_vertical / dist_h)
