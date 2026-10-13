"""Đánh giá MediaPipe (thấy mặt, yaw/pitch) trên FORM (Zenodo 6695771): ảnh cabin thật ban đêm.

Lớp: forward, rotated, on_phonecall, mobile_usage. Tải FORM.zip về data/raw/form/ rồi giải nén.
Chạy: python scripts/eval_form.py
"""

import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from ai.perception.face_landmarks import FaceLandmarkTracker

DIR = ROOT / "data" / "raw" / "form" / "FORM"
OUT = ROOT / "docs" / "experiments" / "form_mediapipe.json"
CLASSES = ("forward", "rotated", "on_phonecall", "mobile_usage")


def observe(path: Path):
    img = Image.open(path).convert("RGB")
    img.thumbnail((640, 640))
    tracker = FaceLandmarkTracker()
    try:
        obs, _, _ = tracker.process(np.array(img), 1.0)
    finally:
        tracker.close()
    return None if obs is None else (obs.yaw, obs.pitch, obs.ear, obs.mar)


def main() -> None:
    res = {}
    for cls in CLASSES:
        files = sorted((DIR / cls).glob("*.jpeg"))
        res[cls] = [observe(p) for p in files]
        print(cls, len(files), flush=True)
    fw = np.array([o for o in res["forward"] if o])
    base_yaw, base_pitch = float(np.median(fw[:, 0])), float(np.median(fw[:, 1]))
    out = {"dataset": "FORM (Zenodo 6695771)", "baseline_forward_median": {"yaw": round(base_yaw, 1), "pitch": round(base_pitch, 1)}}
    for cls, v in res.items():
        d = np.array([o for o in v if o])
        dy = np.abs(d[:, 0] - base_yaw)
        dp = d[:, 1] - base_pitch
        out[cls] = {
            "n": len(v), "face_rate": round(len(d) / len(v), 3),
            "yaw_dev_percentiles": {p: round(float(np.percentile(dy, p)), 1) for p in (10, 50, 90)},
            "pitch_dev_percentiles": {p: round(float(np.percentile(dp, p)), 1) for p in (10, 50, 90)},
            "frac_yaw_dev_gt_30": round(float(np.mean(dy > 30)), 3),
            "frac_pitch_dev_abs_gt_20": round(float(np.mean(np.abs(dp) > 20)), 3),
            "ear_median": round(float(np.median(d[:, 2])), 3),
        }
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps(out, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
