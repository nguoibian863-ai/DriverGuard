"""Đánh giá phát hiện điện thoại + ROI trên FORM (Zenodo 6695771), ảnh cabin thật ban đêm.

Dương tính thật: on_phonecall, mobile_usage. Âm tính: forward, rotated (không cầm điện thoại).
Chạy: python scripts/eval_form_phone.py [số_ảnh_mỗi_lớp=120]
"""

import json
import random
import sys
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from ai.perception.face_landmarks import FaceLandmarkTracker
from ai.perception.phone_detector import PhoneDetector, is_usage_region

DIR = ROOT / "data" / "raw" / "form" / "FORM"
OUT = ROOT / "docs" / "experiments" / "form_phone.json"
N = int(sys.argv[1]) if len(sys.argv) > 1 else 120
CLASSES = ("forward", "rotated", "on_phonecall", "mobile_usage")


def main() -> None:
    det = PhoneDetector()
    out = {"dataset": "FORM (Zenodo 6695771)", "n_per_class": N, "weights": det.model.ckpt_path if hasattr(det.model, "ckpt_path") else "?", "conf": det.conf}
    random.seed(0)
    for cls in CLASSES:
        files = sorted((DIR / cls).glob("*.jpeg"))
        random.shuffle(files)
        n = box = face = usage = usage_noface_hold = 0
        for p in files[:N]:
            img = Image.open(p).convert("RGB")
            img.thumbnail((640, 640))
            rgb = np.array(img)
            bgr = rgb[:, :, ::-1].copy()
            boxes = det.detect(bgr)
            tracker = FaceLandmarkTracker()
            try:
                obs, fbox, _ = tracker.process(rgb, 1.0)
            finally:
                tracker.close()
            n += 1
            box += bool(boxes)
            face += fbox is not None
            usage += bool(boxes) and fbox is not None and any(is_usage_region(b, fbox) for b in boxes)
        out[cls] = {"n": n, "phone_box": round(box / n, 3), "face_found": round(face / n, 3), "phone_usage_roi": round(usage / n, 3)}
        print(cls, out[cls], flush=True)
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
