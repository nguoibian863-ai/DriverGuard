# Đánh giá EAR (MediaPipe) phân biệt mắt nhắm / mở trên MichalMlodawski/closed-open-eyes (ảnh khuôn mặt do AI sinh).
# Chạy từ thư mục gốc dự án: python scripts/eval_eye_state.py [số_phần=20] [thư_mục_cache]
# Kết quả: docs/experiments/eye_state_synthetic.json. Xem docs/EXPERIMENT_LOG.md mục 9.
import io
import json
import os
import random
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import numpy as np
import pyarrow.parquet as pq
import requests
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

DS = "MichalMlodawski/closed-open-eyes"
N_SHARDS = int(sys.argv[1]) if len(sys.argv) > 1 else 20
CACHE = Path(sys.argv[2]) if len(sys.argv) > 2 else Path("eye_cache")
OUT = ROOT / "docs" / "experiments" / "eye_state_synthetic.json"


def list_shards() -> list[str]:
    info = requests.get(f"https://huggingface.co/api/datasets/{DS}", timeout=60).json()
    names = sorted(s["rfilename"] for s in info["siblings"] if s["rfilename"].startswith("data/") and s["rfilename"].endswith(".parquet"))
    return names


def fetch(name: str) -> Path:
    out = CACHE / Path(name).name
    if out.exists():
        return out
    for _ in range(4):
        try:
            r = requests.get(f"https://huggingface.co/datasets/{DS}/resolve/main/{name}", timeout=180)
            r.raise_for_status()
            out.write_bytes(r.content)
            return out
        except Exception:
            continue
    raise RuntimeError(name)


def ear_for(args):
    label, jpeg = args
    from ai.perception.face_landmarks import FaceLandmarkTracker

    img = np.array(Image.open(io.BytesIO(jpeg)).convert("RGB"))
    tracker = FaceLandmarkTracker()
    try:
        obs, _, _ = tracker.process(img, 1.0)
    finally:
        tracker.close()
    return label, (None if obs is None else obs.ear)


def auc(pos: list[float], neg: list[float]) -> float:
    """AUC: xác suất EAR(mắt mở) > EAR(mắt nhắm) (bằng Mann-Whitney)."""
    x = np.concatenate([pos, neg])
    ranks = x.argsort().argsort() + 1.0
    r_pos = ranks[: len(pos)].sum()
    return float((r_pos - len(pos) * (len(pos) + 1) / 2) / (len(pos) * len(neg)))


def metrics(open_ear, closed_ear, thr):
    """Dương tính = 'nhắm mắt' khi EAR < thr."""
    tp = int(sum(e < thr for e in closed_ear))
    fn = len(closed_ear) - tp
    fp = int(sum(e < thr for e in open_ear))
    tn = len(open_ear) - fp
    p = tp / (tp + fp) if tp + fp else 0.0
    r = tp / (tp + fn) if tp + fn else 0.0
    f1 = 2 * p * r / (p + r) if p + r else 0.0
    return dict(thr=round(float(thr), 3), P=round(p, 3), R=round(r, 3), F1=round(f1, 3), FPR=round(fp / (fp + tn), 3), tp=tp, fp=fp, fn=fn, tn=tn)


def main():
    CACHE.mkdir(parents=True, exist_ok=True)
    shards = list_shards()
    idx = np.linspace(0, len(shards) - 1, N_SHARDS).round().astype(int)
    chosen = [shards[i] for i in sorted(set(idx))]
    print("tổng phần:", len(shards), "| chọn:", len(chosen), flush=True)
    with ThreadPoolExecutor(8) as ex:
        files = list(ex.map(fetch, chosen))
    items = []
    for f in files:
        for row in pq.read_table(f).to_pylist():
            blob = row["Image_data"]["file"]
            items.append((row["Label"], blob if isinstance(blob, bytes) else blob["bytes"]))
    random.seed(0)
    random.shuffle(items)
    print("ảnh:", len(items), flush=True)
    res = []
    with ThreadPoolExecutor(4) as ex:
        for i, r in enumerate(ex.map(ear_for, items)):
            res.append(r)
            if (i + 1) % 400 == 0:
                print(i + 1, flush=True)
    labels = sorted({l for l, _ in res})
    print("nhãn:", labels, flush=True)
    out = {"dataset": DS, "n_images": len(res), "n_shards": len(chosen), "labels": labels, "per_label": {}}
    ears = {}
    for lab in labels:
        e = [v for l, v in res if l == lab and v is not None]
        n = sum(1 for l, _ in res if l == lab)
        ears[lab] = e
        out["per_label"][lab] = dict(n=n, detected=len(e), detect_rate=round(len(e) / n, 3),
                                     ear_percentiles={p: round(float(np.percentile(e, p)), 3) for p in (1, 5, 25, 50, 75, 95, 99)} if e else {})
    closed_key = next(l for l in labels if "closed" in l)
    open_key = next(l for l in labels if "open" in l)
    oe, ce = ears[open_key], ears[closed_key]
    out["auc_open_gt_closed"] = round(auc(oe, ce), 4)
    out["fixed_0.20"] = metrics(oe, ce, 0.20)
    best = max((metrics(oe, ce, t) for t in np.arange(0.05, 0.40, 0.005)), key=lambda m: m["F1"])
    out["best_f1"] = best
    out["sweep"] = [metrics(oe, ce, t) for t in (0.10, 0.12, 0.15, 0.18, 0.20, 0.22, 0.25, 0.28, 0.30)]
    out["open_eyes_below_0.20_fraction"] = round(float(np.mean([e < 0.20 for e in oe])), 3)
    out["closed_eyes_above_0.20_fraction"] = round(float(np.mean([e >= 0.20 for e in ce])), 3)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps({k: v for k, v in out.items() if k != "sweep"}, ensure_ascii=False, indent=1), flush=True)


if __name__ == "__main__":
    main()
