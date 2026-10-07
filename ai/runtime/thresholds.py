"""Nạp ngưỡng từ ai/config/thresholds.yaml."""

from dataclasses import dataclass, fields
from pathlib import Path

import yaml

CONFIG_PATH = Path(__file__).resolve().parents[1] / "config" / "thresholds.yaml"


@dataclass
class Thresholds:
    ear_threshold: float = 0.15
    eyes_closed_s: float = 1.8
    mar_threshold: float = 0.40
    yawn_s: float = 2.0
    yaw_threshold: float = 30.0
    pitch_threshold: float = 20.0
    head_s: float = 2.0
    phone_s: float = 1.5
    absence_s: float = 3.0
    cooldown_s: float = 3.0
    calibration_s: float = 4.0
    perclos_window_s: float = 60.0
    yawn_window_s: float = 300.0
    pitch_sign: float = 1.0
    use_pose_fallback: bool = False
    pose_yaw_ratio: float = 0.35
    pose_pitch_ratio: float = 0.30
    pose_max_age_s: float = 0.6


def load_thresholds(path: Path = CONFIG_PATH) -> Thresholds:
    """Đọc yaml; khóa thiếu dùng mặc định, khóa lạ bị bỏ qua."""
    if not path.exists():
        return Thresholds()
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    definitions = {f.name: f for f in fields(Thresholds)}
    values = {}
    for key, value in data.items():
        field = definitions.get(key)
        if field is None:
            continue
        if field.type is bool:
            values[key] = value if isinstance(value, bool) else str(value).lower() in {"1", "true", "yes", "on"}
        else:
            values[key] = float(value)
    return Thresholds(**values)
