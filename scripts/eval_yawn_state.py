# Đánh giá MAR (MediaPipe) phân biệt ngáp / không ngáp trên c3rl/yawning-people (ảnh khuôn mặt do AI sinh).
# Chạy từ thư mục gốc dự án: python scripts/eval_yawn_state.py [số_ảnh_mỗi_lớp=400] [thư_mục_cache]
# Kết quả: docs/experiments/yawn_state_synthetic.json. Xem docs/EXPERIMENT_LOG.md mục 10.
import io
import json
import random
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import numpy as np
import requests
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

DS = "c3rl/yawning-people"
N = int(sys.argv[1]) if len(sys.argv) > 1 else 400
CACHE = Path(sys.argv[2]) if len(sys.argv) > 2 else Path("yawn_cache")
OUT = ROOT / "docs" / "experiments" / "yawn_state_synthetic.json"


def list_images() -> dict[str, list[str]]:
    info = requests.get(f"https://huggingface.co/api/datasets/{DS}", timeout=60).json()
    names = [s["rfilename"] for s in info["siblings"] if s["rfilename"].endswith(".png") and ".ipynb_checkpoints" not in s["rfilename"]]
    return {"yawning": sorted(n for n in names if "/yawning/" in n), "notyawning": sorted(n for n in names if "/notyawning/" in n)}


def fetch(name: str) -> bytes:
    out = CACHE / name.replace("/", "_")
    if out.exists():
        return out.read_bytes()
    for _ in range(4):
        try:
            r = requests.get(f"https://huggingface.co/datasets/{DS}/resolve/main/{name}", timeout=180)
            r.raise_for_status()
            out.write_bytes(r.content)
            return r.content
        except Exception:
            continue
    raise RuntimeError(name)


def mar_for(args):
    label, png = args
    from ai.perception.face_landmarks import FaceLandmarkTracker

    img = np.array(Image.open(io.BytesIO(png)).convert("RGB"))
    tracker = FaceLandmarkTracker()
    try:
        obs, _, _ = tracker.process(img, 1.0)
    finally:
        tracker.close()
    return label, (None if obs is None else obs.mar)


def auc(pos, neg) -> float:
    """AUC: xác suất MAR(ngáp) > MAR(không ngáp) (Mann-Whitney)."""
    x = np.concatenate([pos, neg])
    ranks = x.argsort().argsort() + 1.0
    return float((ranks[: len(pos)].sum() - len(pos) * (len(pos) + 1) / 2) / (len(pos) * len(neg)))


def metrics(yawn, notyawn, thr):
    """Dương tính = 'ngáp' khi MAR > thr."""
    tp = int(sum(m > thr for m in yawn))
    fn = len(yawn) - tp
    fp = int(sum(m > thr for m in notyawn))
    tn = len(notyawn) - fp
    p = tp / (tp + fp) if tp + fp else 0.0
    r = tp / (tp + fn) if tp + fn else 0.0
    f1 = 2 * p * r / (p + r) if p + r else 0.0
    return dict(thr=round(float(thr), 3), P=round(p, 3), R=round(r, 3), F1=round(f1, 3), FPR=round(fp / (fp + tn), 3), tp=tp, fp=fp, fn=fn, tn=tn)


def main():
    CACHE.mkdir(parents=True, exist_ok=True)
    allimg = list_images()
    random.seed(0)
    chosen = {k: random.sample(v, min(N, len(v))) for k, v in allimg.items()}
    print({k: (len(allimg[k]), len(v)) for k, v in chosen.items()}, flush=True)
    jobs = [(k, n) for k, v in chosen.items() for n in v]
    with ThreadPoolExecutor(12) as ex:
        blobs = list(ex.map(lambda j: (j[0], fetch(j[1])), jobs))
    print("đã tải", len(blobs), flush=True)
    res = []
    with ThreadPoolExecutor(4) as ex:
        for i, r in enumerate(ex.map(mar_for, blobs)):
            res.append(r)
            if (i + 1) % 200 == 0:
                print(i + 1, flush=True)
    out = {"dataset": DS, "n_per_class": N, "per_label": {}}
    mars = {}
    for lab in ("yawning", "notyawning"):
        m = [v for l, v in res if l == lab and v is not None]
        n = sum(1 for l, _ in res if l == lab)
        mars[lab] = m
        out["per_label"][lab] = dict(n=n, detected=len(m), detect_rate=round(len(m) / n, 3),
                                     mar_percentiles={p: round(float(np.percentile(m, p)), 3) for p in (1, 5, 25, 50, 75, 95, 99)} if m else {})
    ym, nm = mars["yawning"], mars["notyawning"]
    out["auc_yawn_gt_notyawn"] = round(auc(ym, nm), 4)
    out["fixed_0.60"] = metrics(ym, nm, 0.60)
    out["best_f1"] = max((metrics(ym, nm, t) for t in np.arange(0.05, 1.20, 0.01)), key=lambda m: m["F1"])
    out["sweep"] = [metrics(ym, nm, t) for t in (0.20, 0.30, 0.40, 0.50, 0.60, 0.70, 0.80)]
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps({k: v for k, v in out.items() if k != "sweep"}, ensure_ascii=False, indent=1), flush=True)
    print("SWEEP", json.dumps(out["sweep"], ensure_ascii=False), flush=True)


if __name__ == "__main__":
    main()
