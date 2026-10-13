"""So sánh trạng thái TỈNH TÁO và MỆT MỎI trên video thật (tập DF, figshare, CC BY 4.0).

Nguồn: "DF-vediodataset" part1-4 (figshare 33100853/33102506/33103226/33107144), video mô phỏng
lái tàu, tên tệp có nhãn 清醒 (tỉnh táo) hoặc 疲劳 (mệt mỏi). Tải vài cặp cùng một người vào
data/raw/df_video/.

Đo bằng chính pipeline của dự án: PERCLOS, số lần nhắm mắt dài, ngáp, và sự kiện sinh ra.
Chạy: python scripts/eval_df_video.py [--stride 2]
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ai.perception.face_landmarks import FaceLandmarkTracker
from ai.runtime.pipeline import DriverPipeline
from ai.runtime.thresholds import load_thresholds

DATA_DIR = ROOT / "data" / "raw" / "df_video"
OUT = ROOT / "docs" / "experiments" / "df_video.json"
ALERT, FATIGUE = "清醒", "疲劳"


def label_of(path: Path) -> str | None:
    if ALERT in path.name:
        return "alert"
    if FATIGUE in path.name:
        return "fatigue"
    return None


def run_video(video: Path, stride: int) -> dict:
    thresholds = load_thresholds()
    pipeline = DriverPipeline(thresholds)
    tracker = FaceLandmarkTracker()
    capture = cv2.VideoCapture(str(video))
    fps = capture.get(cv2.CAP_PROP_FPS) or 30.0

    ears: list[float] = []
    mars: list[float] = []
    closed_flags: list[bool] = []
    events: list[dict] = []
    faces = processed = index = 0
    elapsed = 0.0
    try:
        while True:
            ok, frame = capture.read()
            if not ok:
                break
            index += 1
            if (index - 1) % stride:
                continue
            now = (index - 1) / fps
            started = time.perf_counter()
            observation, _, _ = tracker.process(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB), now)
            telemetry, new_events = pipeline.update(now, observation)
            elapsed += time.perf_counter() - started
            processed += 1
            events.extend(new_events)
            if observation is not None:
                faces += 1
                ears.append(observation.ear)
                mars.append(observation.mar)
            closed_flags.append(bool(telemetry["eyes_closed"]))
    finally:
        capture.release()
        tracker.close()

    minutes = index / fps / 60.0
    counts: dict[str, int] = {}
    for event in events:
        counts[event["event_type"]] = counts.get(event["event_type"], 0) + 1
    return {
        "video": video.name,
        "label": label_of(video),
        "minutes": round(minutes, 2),
        "frames_processed": processed,
        "face_rate": round(faces / max(processed, 1), 3),
        "ear_median": round(float(np.median(ears)), 3) if ears else None,
        "ear_p10": round(float(np.percentile(ears, 10)), 3) if ears else None,
        "mar_p95": round(float(np.percentile(mars, 95)), 3) if mars else None,
        # PERCLOS: tỉ lệ khung bị coi là nhắm mắt (sau khi pipeline đã bỏ qua lúc cúi/ngáp)
        "perclos": round(sum(closed_flags) / max(processed, 1), 4),
        "events": counts,
        "events_per_min": {k: round(v / minutes, 3) for k, v in counts.items()} if minutes else {},
        "ms_per_frame": round(elapsed / max(processed, 1) * 1000, 1),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--stride", type=int, default=2, help="xử lý mỗi N khung (video 30 FPS)")
    parser.add_argument("--out", type=Path, default=OUT)
    args = parser.parse_args()

    videos = sorted(p for p in DATA_DIR.glob("*.mp4") if label_of(p))
    if not videos:
        raise SystemExit(f"không thấy video có nhãn trong {DATA_DIR}")

    results = []
    for video in videos:
        result = run_video(video, args.stride)
        results.append(result)
        print(json.dumps(result, ensure_ascii=False), flush=True)

    def agg(label: str) -> dict:
        rows = [r for r in results if r["label"] == label]
        minutes = sum(r["minutes"] for r in rows)
        frames = sum(r["frames_processed"] for r in rows)
        drowsy = sum(r["events"].get("DROWSINESS_ACUTE", 0) for r in rows)
        return {
            "videos": len(rows),
            "minutes": round(minutes, 1),
            "perclos": round(sum(r["perclos"] * r["frames_processed"] for r in rows) / max(frames, 1), 4),
            "ear_median": round(float(np.median([r["ear_median"] for r in rows if r["ear_median"]])), 3) if rows else None,
            "DROWSINESS_ACUTE": drowsy,
            "DROWSINESS_ACUTE_per_min": round(drowsy / minutes, 3) if minutes else None,
            "YAWNING": sum(r["events"].get("YAWNING", 0) for r in rows),
            "CHRONIC_FATIGUE": sum(r["events"].get("CHRONIC_FATIGUE", 0) for r in rows),
        }

    summary = {
        "dataset": "DF-vediodataset (figshare, CC BY 4.0)",
        "stride": args.stride,
        "thresholds": {"ear": load_thresholds().ear_threshold, "eyes_closed_s": load_thresholds().eyes_closed_s},
        "alert": agg("alert"),
        "fatigue": agg("fatigue"),
        "per_video": results,
    }
    args.out.write_text(json.dumps(summary, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps({k: v for k, v in summary.items() if k != "per_video"}, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
