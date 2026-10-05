# Đánh giá phát hiện điện thoại (YOLO26 n/s/m/l/x) + MediaPipe mặt trên mẫu State Farm. Chạy trong thư mục có cache/ của fetch_state_farm_sample.py.
import glob, json, os, sys, time
import cv2, numpy as np, torch
from ultralytics import YOLO
sys.path.insert(0, "D:/Dự Án Cá Nhân/DriverGuard_Documentation")
from ai.perception.face_landmarks import FaceLandmarkTracker
from ai.perception.phone_detector import is_usage_region

PHONE_CLASSES = {"c1", "c2", "c3", "c4"}      # texting/talking, trái/phải
NAMES = {"c0": "lái an toàn", "c1": "nhắn tin (phải)", "c2": "gọi (phải)", "c3": "nhắn tin (trái)", "c4": "gọi (trái)",
         "c5": "chỉnh radio", "c6": "uống nước", "c7": "với ra sau", "c8": "trang điểm/tóc", "c9": "nói chuyện với hành khách"}
files = sorted(glob.glob("cache/c*/*.jpg"))
print("ảnh:", len(files), flush=True)

# 1) Khuôn mặt (MediaPipe) - tạo mới mỗi ảnh để không rò rỉ tracking giữa các ảnh
faces = {}
t0 = time.time()
for i, f in enumerate(files):
    img = cv2.imread(f)
    tr = FaceLandmarkTracker()
    obs, box, _ = tr.process(cv2.cvtColor(img, cv2.COLOR_BGR2RGB), 1.0); tr.close()
    faces[f] = box
print(f"mặt xong {time.time()-t0:.0f}s", flush=True)

# 2) YOLO: một lần suy luận ở conf thấp (0.10), lọc theo nhiều ngưỡng sau
MODELS = ["yolo26n.pt", "yolo26s.pt", "yolo26m.pt", "yolo26l.pt", "yolo26x.pt"]
dets = {}
lat = {}
for name in MODELS:
    m = YOLO(name); ms = []
    for f in files[:3]: m.predict(f, classes=[67], conf=0.1, device=0, verbose=False, imgsz=640)
    d = {}
    for f in files:
        t = time.time()
        r = m.predict(f, classes=[67], conf=0.1, device=0, verbose=False, imgsz=640)[0]
        ms.append((time.time() - t) * 1000)
        d[f] = [(float(s), tuple(int(v) for v in b)) for s, b in zip(r.boxes.conf.cpu().numpy(), r.boxes.xyxy.cpu().numpy())]
    dets[name] = d; lat[name] = float(np.median(ms))
    print(name, f"{lat[name]:.1f} ms", flush=True)

def cls(f): return os.path.basename(os.path.dirname(f))
def stats(pred_fn):
    tp = fp = fn = tn = 0
    per = {}
    for f in files:
        c = cls(f); pos = c in PHONE_CLASSES; p = pred_fn(f)
        per.setdefault(c, [0, 0]); per[c][0] += int(p); per[c][1] += 1
        if pos and p: tp += 1
        elif pos: fn += 1
        elif p: fp += 1
        else: tn += 1
    P = tp / (tp + fp) if tp + fp else 0; R = tp / (tp + fn) if tp + fn else 0
    F = 2 * P * R / (P + R) if P + R else 0
    return dict(P=P, R=R, F1=F, FPR=fp / (fp + tn), per={k: v[0] / v[1] for k, v in per.items()}, tp=tp, fp=fp, fn=fn, tn=tn)

res = {"n_images": len(files), "latency_ms": lat, "face_rate": {}, "results": []}
for c in sorted({cls(f) for f in files}):
    fs = [f for f in files if cls(f) == c]; res["face_rate"][c] = sum(faces[f] is not None for f in fs) / len(fs)
for name in MODELS:
    for conf in (0.10, 0.25, 0.40):
        box_pred = lambda f: any(s >= conf for s, _ in dets[name][f])
        use_pred = lambda f: any(s >= conf and is_usage_region(b, faces[f]) for s, b in dets[name][f])
        res["results"].append({"model": name, "conf": conf, "box": stats(box_pred), "usage": stats(use_pred)})
json.dump(res, open("sf_results.json", "w"), ensure_ascii=False, indent=1)
print("tỉ lệ thấy mặt theo lớp:", {k: round(v, 2) for k, v in res["face_rate"].items()})
for r in res["results"]:
    b, u = r["box"], r["usage"]
    print(f'{r["model"]:11s} conf={r["conf"]:.2f} | CÓ-BOX P={b["P"]:.2f} R={b["R"]:.2f} F1={b["F1"]:.2f} FPR={b["FPR"]:.2f} | PHONE_USAGE(có ROI+mặt) P={u["P"]:.2f} R={u["R"]:.2f} F1={u["F1"]:.2f} FPR={u["FPR"]:.2f}')
