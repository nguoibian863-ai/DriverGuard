"""Đánh giá độc lập EAR/MAR trên Driver Drowsiness Dataset (HF akahana/Driver-Drowsiness-Dataset).

Nhãn ảnh: Drowsy (mắt nhắm/ngáp) và Non Drowsy. Dương tính = EAR < ear_threshold hoặc MAR > mar_threshold.
Chạy: python scripts/eval_ddd_hf.py [parquet] [số_ảnh=1500]   (mặc định data/raw/ddd/test-0.parquet)
"""

import io
import json
import random
import sys
from pathlib import Path

import numpy as np
import pyarrow.parquet as pq
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from ai.perception.face_landmarks import FaceLandmarkTracker
from ai.runtime.thresholds import load_thresholds

PARQUET = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "data" / "raw" / "ddd" / "test-0.parquet"
N = int(sys.argv[2]) if len(sys.argv) > 2 else 1500
OUT = ROOT / "docs" / "experiments" / "ddd_hf.json"


def auc(pos, neg) -> float:
    """P(điểm dương > điểm âm), Mann-Whitney."""
    x = np.concatenate([pos, neg])
    ranks = x.argsort().argsort() + 1.0
    return float((ranks[: len(pos)].sum() - len(pos) * (len(pos) + 1) / 2) / (len(pos) * len(neg)))


def main() -> None:
    th = load_thresholds()
    rows = pq.read_table(PARQUET).to_pylist()
    random.seed(0)
    random.shuffle(rows)
    rows = rows[:N]
    res = []
    for i, r in enumerate(rows):
        img = np.array(Image.open(io.BytesIO(r["image"]["bytes"])).convert("RGB"))
        tracker = FaceLandmarkTracker()
        try:
            obs, _, _ = tracker.process(img, 1.0)
        finally:
            tracker.close()
        res.append((r["label"], None if obs is None else (obs.ear, obs.mar)))
        if (i + 1) % 300 == 0:
            print(i + 1, flush=True)
    out = {"dataset": "akahana/Driver-Drowsiness-Dataset", "parquet": PARQUET.name, "n": len(res),
           "ear_thr": th.ear_threshold, "mar_thr": th.mar_threshold}
    for lab, name in ((0, "drowsy"), (1, "non_drowsy")):
        v = [x for l, x in res if l == lab]
        d = [x for x in v if x is not None]
        out[name] = {"n": len(v), "detect_rate": round(len(d) / len(v), 3),
                     "ear_median": round(float(np.median([x[0] for x in d])), 3),
                     "mar_median": round(float(np.median([x[1] for x in d])), 3)}
    dz = [x for l, x in res if l == 0 and x]
    nz = [x for l, x in res if l == 1 and x]
    out["auc_ear"] = round(auc([-x[0] for x in dz], [-x[0] for x in nz]), 4)
    out["auc_mar"] = round(auc([x[1] for x in dz], [x[1] for x in nz]), 4)

    def flag(x, ear_t, mar_t):
        return x[0] < ear_t or x[1] > mar_t

    def rates(ear_t, mar_t):
        tp = sum(flag(x, ear_t, mar_t) for x in dz)
        fp = sum(flag(x, ear_t, mar_t) for x in nz)
        return {"ear_t": ear_t, "mar_t": mar_t, "recall": round(tp / len(dz), 3), "fpr": round(fp / len(nz), 3)}

    out["at_config"] = rates(th.ear_threshold, th.mar_threshold)
    out["sweep_ear"] = [rates(t, 9.0) for t in (0.12, 0.15, 0.18, 0.20, 0.22, 0.25)]
    out["sweep_mar"] = [rates(-1.0, t) for t in (0.30, 0.40, 0.50, 0.60)]
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps(out, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
