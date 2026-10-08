# Biến thể của eval_phone_coco.py: so sánh các cỡ yolo26 (s/m/l) ở imgsz 640. Xem docs/EXPERIMENT_LOG.md.
import io, json, random, sys, time
import numpy as np, pyarrow.parquet as pq, torch
from PIL import Image
from ultralytics import YOLO

random.seed(0)
PHONE = 67
def load(files):
    pos, neg = [], []
    for f in files:
        t = pq.read_table(f).to_pylist()
        for r in t:
            cats = r["objects"]["category"]
            item = (r["image"]["bytes"], r["width"], r["height"],
                    [b for b, c in zip(r["objects"]["bbox"], cats) if c == PHONE])
            (pos if PHONE in cats else neg).append(item)
    return pos, neg

pos, neg = load(["val0.parquet", "val1.parquet"])
print("ảnh có điện thoại:", len(pos), "| hộp:", sum(len(p[3]) for p in pos), "| ảnh không có:", len(neg), flush=True)
neg = random.sample(neg, 400)
# kiểm tra định dạng bbox: xyxy hay xywh
bad_xyxy = sum(1 for p in pos for b in p[3] if b[2] <= b[0] or b[3] <= b[1])
bad_xywh = sum(1 for p in pos for b in p[3] if b[0] + b[2] > p[1] + 2 or b[1] + b[3] > p[2] + 2)
print("bbox xyxy không hợp lệ:", bad_xyxy, "| xywh vượt khung:", bad_xywh, flush=True)

def iou(a, b):
    ix = max(0, min(a[2], b[2]) - max(a[0], b[0])); iy = max(0, min(a[3], b[3]) - max(a[1], b[1]))
    inter = ix * iy; u = (a[2]-a[0])*(a[3]-a[1]) + (b[2]-b[0])*(b[3]-b[1]) - inter
    return inter / u if u > 0 else 0

def img(item):
    return np.array(Image.open(io.BytesIO(item[0])).convert("RGB"))[:, :, ::-1].copy()

def run(model, imgsz, conf, label):
    dev = 0 if torch.cuda.is_available() else "cpu"
    tp = fp = fn = 0; fp_neg = 0; ms = []
    tp_l = fn_l = 0  # hộp lớn (>= 2% diện tích ảnh): giống điện thoại cầm gần camera
    for item in pos:
        im = img(item); t = time.time()
        r = model.predict(im, classes=[PHONE], conf=conf, device=dev, verbose=False, imgsz=imgsz)[0]; ms.append((time.time()-t)*1000)
        preds = sorted([(float(s), b) for s, b in zip(r.boxes.conf.cpu().numpy(), r.boxes.xyxy.cpu().numpy())], key=lambda x: -x[0])
        used = set()
        for gi, g in enumerate(item[3]):
            large = (g[2]-g[0])*(g[3]-g[1]) >= 0.02 * item[1] * item[2]
            hit = None
            for pi, (s, b) in enumerate(preds):
                if pi not in used and iou(g, b) >= 0.5: hit = pi; break
            if hit is not None: used.add(hit); tp += 1; tp_l += large
            else: fn += 1; fn_l += large
        fp += len(preds) - len(used)
    for item in neg:
        r = model.predict(img(item), classes=[PHONE], conf=conf, device=dev, verbose=False, imgsz=imgsz)[0]
        fp_neg += len(r.boxes)
    prec = tp / (tp + fp) if tp + fp else 0; rec = tp / (tp + fn) if tp + fn else 0
    f1 = 2 * prec * rec / (prec + rec) if prec + rec else 0
    rec_l = tp_l / (tp_l + fn_l) if tp_l + fn_l else 0
    print(f"{label:22s} imgsz={imgsz} conf={conf}: P={prec:.2f} R={rec:.2f} F1={f1:.2f} | R(hộp lớn)={rec_l:.2f} (n={tp_l+fn_l}) | báo giả trên {len(neg)} ảnh không điện thoại: {fp_neg} ({fp_neg/len(neg):.3f}/ảnh) | {np.median(ms):.1f} ms", flush=True)

import torch
for name in ["yolo26s.pt", "yolo26m.pt", "yolo26l.pt"]:
    m = YOLO(name)
    for imgsz, conf in ((640, 0.25),):
        torch.cuda.reset_peak_memory_stats()
        run(m, imgsz, conf, name)
        print(f"    VRAM đỉnh: {torch.cuda.max_memory_allocated()/2**20:.0f} MiB", flush=True)
    print(f"    tham số: {sum(p.numel() for p in m.model.parameters())/1e6:.1f}M", flush=True)
