"""Đánh giá MAR (ngáp) trên HF c3rl/yawning-people (ảnh do AI sinh, nhãn yawning/notyawning).

Tải trước ảnh vào data/raw/yawn/images/{yawning,notyawning}/ (xem docs/EXPERIMENT_LOG.md mục 20).
Chạy: python scripts/eval_yawn_hf.py [thư_mục=data/raw/yawn/images]
"""

import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from ai.perception.face_landmarks import FaceLandmarkTracker

IMG_DIR = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "data" / "raw" / "yawn" / "images"
OUT = ROOT / "docs" / "experiments" / "yawn_hf.json"


def auc(pos, neg) -> float:
    x = np.concatenate([pos, neg])
    ranks = x.argsort().argsort() + 1.0
    return float((ranks[: len(pos)].sum() - len(pos) * (len(pos) + 1) / 2) / (len(pos) * len(neg)))


def mar_for(path: Path):
    img = np.array(Image.open(path).convert("RGB"))
    tracker = FaceLandmarkTracker()
    try:
        obs, _, _ = tracker.process(img, 1.0)
    finally:
        tracker.close()
    return None if obs is None else obs.mar


def main() -> None:
    data = {}
    for cls in ("yawning", "notyawning"):
        files = sorted((IMG_DIR / cls).glob("*.png"))
        data[cls] = [mar_for(p) for p in files]
        print(cls, len(files), flush=True)
    out = {"dataset": "c3rl/yawning-people (ảnh sinh bởi AI)"}
    pos = [m for m in data["yawning"] if m is not None]
    neg = [m for m in data["notyawning"] if m is not None]
    for cls, v in data.items():
        d = [m for m in v if m is not None]
        out[cls] = {"n": len(v), "detect_rate": round(len(d) / len(v), 3),
                    "mar_percentiles": {p: round(float(np.percentile(d, p)), 3) for p in (5, 25, 50, 75, 95)}}
    out["auc_mar"] = round(auc(pos, neg), 4)
    out["sweep"] = [
        {"mar_t": t, "recall": round(float(np.mean([m > t for m in pos])), 3),
         "fpr": round(float(np.mean([m > t for m in neg])), 3)}
        for t in (0.20, 0.30, 0.40, 0.50, 0.60)
    ]
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps(out, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
