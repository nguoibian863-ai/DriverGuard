# Phát lại docs/experiments/live_session.json qua DriverPipeline hiện tại để kiểm tra cờ/sự kiện theo pha. Chạy từ thư mục gốc: python scripts/replay_live_session.py
import json, sys
sys.path.insert(0, ".")
from ai.runtime.pipeline import DriverPipeline, FaceObservation, PhoneObservation
from ai.runtime.thresholds import load_thresholds
d = json.load(open("docs/experiments/live_session.json", encoding="utf-8"))
frames, marks, steps = d["frames"], d["marks"], d["steps"]
bounds = [(m["phase"], m["t"]) for m in marks]
def phase_of(t):
    p = None
    for n, mt in bounds:
        if t >= mt: p = n
    return p
th = load_thresholds()
print("ngưỡng: ear_fallback", th.ear_threshold, "| mar", th.mar_threshold, "| yaw", th.yaw_threshold, "| pitch", th.pitch_threshold)
pipe = DriverPipeline(th)
# bắt đầu từ pha baseline (người dùng đã vào tư thế)
start = bounds[0][1]
ev_by_phase, flags_by_phase = {}, {}
for f in frames:
    if f["t"] < start: continue
    face = FaceObservation(f["ear"], f["mar"], f["yaw"], f["pitch"], 0.0) if f["face_detected"] else None
    tele, events = pipe.update(f["t"], face, PhoneObservation(f["phone_detected"], False))
    ph = phase_of(f["t"])
    for e in events: ev_by_phase.setdefault(ph, []).append(e["event_type"])
    for k in ("eyes_closed", "yawning", "looking_away", "looking_down"):
        if tele[k]: flags_by_phase.setdefault(ph, set()).add(k)
print("ear_baseline (từ 4 giây đầu):", round(pipe.ear_baseline, 3), "-> ngưỡng nhắm mắt", round(pipe.ear_threshold, 3))
expect = {"eyes_closed": "DROWSINESS_ACUTE", "look_down": "LOOKING_DOWN", "yawn": "YAWNING", "look_left": "LOOKING_AWAY", "look_right": "LOOKING_AWAY"}
print(f'{"pha":12s} {"cờ":38s} sự kiện')
for n, _, _ in steps:
    if n in ("end",): continue
    print(f'{n:12s} {str(sorted(flags_by_phase.get(n, []))):38s} {sorted(set(ev_by_phase.get(n, [])))}')
