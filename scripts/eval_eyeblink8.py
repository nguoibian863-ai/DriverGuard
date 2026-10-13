"""Chạy pipeline thật trên video eyeblink8 (nhãn nháy mắt từng khung) để đo báo giả theo thời gian.

Nguồn: https://www.blinkingmatters.com/research (Fogelton & Benesova), 8 video 640x480 30 FPS,
4 người, 408 lần nháy mắt có nhãn. Giải nén vào data/raw/eyeblink8/.

Câu hỏi chính: nháy mắt bình thường có làm hệ thống báo DROWSINESS_ACUTE nhầm không,
và bao nhiêu lần mỗi phút. Đây là số liệu trên VIDEO nên có chiều thời gian, khác các
thí nghiệm ảnh tĩnh (mục 9, 19 của docs/EXPERIMENT_LOG.md).

Chạy: python scripts/eval_eyeblink8.py [--stride N] [--videos 1,2]
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

DATA_DIR = ROOT / "data" / "raw" / "eyeblink8" / "eyeblink8"
OUT = ROOT / "docs" / "experiments" / "eyeblink8.json"


def read_tags(path: Path) -> dict[int, dict]:
    """Đọc .tag: frame:blink_id:NF:LE_FC:LE_NV:RE_FC:RE_NV:... ('C' = nhắm hẳn)."""
    tags: dict[int, dict] = {}
    for line in path.read_text(errors="ignore").splitlines():
        parts = line.split(":")
        if len(parts) < 7 or not parts[0].isdigit():
            continue
        tags[int(parts[0])] = {
            "blink": parts[1] != "-1",
            "closed": parts[3] == "C" or parts[5] == "C",
        }
    return tags


def spans_of(tags: dict[int, dict], key: str) -> list[tuple[int, int]]:
    """Các đoạn khung liên tiếp cùng được đánh dấu theo `key` ('blink' hoặc 'closed')."""
    frames = sorted(f for f, t in tags.items() if t[key])
    spans: list[tuple[int, int]] = []
    for frame in frames:
        if spans and frame == spans[-1][1] + 1:
            spans[-1] = (spans[-1][0], frame)
        else:
            spans.append((frame, frame))
    return spans


def closure_latencies(by_frame: dict[int, dict], tags: dict[int, dict], fps: float, ear_threshold: float) -> list[float]:
    """Độ trễ cảm nhận: từ khung ĐẦU TIÊN được đánh nhãn 'nhắm hẳn' đến khung EAR tụt dưới ngưỡng.

    Âm nghĩa là EAR đã tụt TRƯỚC khi nhãn bắt đầu (mắt khép dần trước khi nhắm hẳn), tức không trễ.
    Chỉ tính các đoạn tìm được điểm cắt trong cửa sổ [-0,5 s, +1,0 s] quanh mốc nhãn.
    """
    latencies: list[float] = []
    for start, _ in spans_of(tags, "closed"):
        lo, hi = start - int(0.5 * fps), start + int(1.0 * fps)
        crossing = next(
            (f for f in range(lo, hi + 1)
             if f in by_frame and by_frame[f]["ear"] is not None and by_frame[f]["ear"] < ear_threshold),
            None,
        )
        if crossing is not None:
            latencies.append((crossing - start) / fps)
    return latencies


def run_video(video: Path, tags: dict[int, dict], stride: int) -> dict:
    thresholds = load_thresholds()
    pipeline = DriverPipeline(thresholds)
    tracker = FaceLandmarkTracker()
    capture = cv2.VideoCapture(str(video))
    fps = capture.get(cv2.CAP_PROP_FPS) or 30.0

    rows: list[dict] = []
    events: list[dict] = []
    elapsed = 0.0
    index = -1
    try:
        while True:
            ok, frame = capture.read()
            if not ok:
                break
            index += 1
            if index % stride:
                continue
            now = index / fps  # thời gian theo video, không theo đồng hồ máy
            started = time.perf_counter()
            observation, _, _ = tracker.process(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB), now)
            telemetry, new_events = pipeline.update(now, observation)
            elapsed += time.perf_counter() - started
            events.extend({**event, "frame": index} for event in new_events)
            rows.append({
                "frame": index,
                "face": observation is not None,
                "ear": None if observation is None else observation.ear,
                "eyes_closed": bool(telemetry["eyes_closed"]),
                "calibrated": bool(telemetry["calibrated"]),
                "risk": telemetry["risk_score"],
            })
    finally:
        capture.release()
        tracker.close()

    processed = len(rows)
    duration_min = (index + 1) / fps / 60.0
    truth_closed = {f for f, t in tags.items() if t["closed"]}
    spans = spans_of(tags, "blink")

    # Ở mức khung: EAR dưới ngưỡng so với nhãn "nhắm hẳn"
    seen = [r for r in rows if r["ear"] is not None]
    tp = sum(1 for r in seen if r["ear"] < thresholds.ear_threshold and r["frame"] in truth_closed)
    fp = sum(1 for r in seen if r["ear"] < thresholds.ear_threshold and r["frame"] not in truth_closed)
    fn = sum(1 for r in seen if r["ear"] >= thresholds.ear_threshold and r["frame"] in truth_closed)
    tn = len(seen) - tp - fp - fn

    # Ở mức lần nháy: có khung nào trong đoạn nháy bị EAR hạ dưới ngưỡng không
    by_frame = {r["frame"]: r for r in seen}
    hit = sum(
        1 for start, end in spans
        if any(by_frame[f]["ear"] < thresholds.ear_threshold for f in range(start, end + 1) if f in by_frame)
    )

    latencies = closure_latencies(by_frame, tags, fps, thresholds.ear_threshold)
    drowsy = [e for e in events if e["event_type"] == "DROWSINESS_ACUTE"]
    return {
        "video": f"{video.parent.name}/{video.name}",
        "frames_total": index + 1,
        "frames_processed": processed,
        "duration_min": round(duration_min, 2),
        "fps_video": round(fps, 1),
        "face_rate": round(sum(r["face"] for r in rows) / max(processed, 1), 3),
        "calibrated_rate": round(sum(r["calibrated"] for r in rows) / max(processed, 1), 3),
        "blinks_annotated": len(spans),
        "blinks_with_ear_dip": hit,
        "blink_recall": round(hit / len(spans), 3) if spans else None,
        "frame_level": {"tp": tp, "fp": fp, "fn": fn, "tn": tn,
                        "recall": round(tp / (tp + fn), 3) if tp + fn else None,
                        "fpr": round(fp / (fp + tn), 4) if fp + tn else None},
        "closure_latency_s": {
            "n": len(latencies),
            "median": round(float(np.median(latencies)), 3) if latencies else None,
            "p90": round(float(np.percentile(latencies, 90)), 3) if latencies else None,
        },
        "events": {e: sum(1 for x in events if x["event_type"] == e) for e in sorted({x["event_type"] for x in events})},
        "false_drowsiness_per_min": round(len(drowsy) / duration_min, 3) if duration_min else None,
        "ms_per_frame": round(elapsed / max(processed, 1) * 1000, 1),
    }


def _latency_summary(results: list[dict]) -> dict:
    """Gộp độ trễ theo trung vị có trọng số số đoạn của từng video."""
    rows = [r for r in results if r["closure_latency_s"]["median"] is not None]
    total = sum(r["closure_latency_s"]["n"] for r in rows)
    if not total:
        return {"n": 0, "median_of_videos": None}
    return {
        "n": total,
        "median_of_videos": round(float(np.median([r["closure_latency_s"]["median"] for r in rows])), 3),
        "p90_of_videos": round(float(np.median([r["closure_latency_s"]["p90"] for r in rows])), 3),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--stride", type=int, default=1, help="chỉ xử lý mỗi N khung (1 = tất cả)")
    parser.add_argument("--videos", default="", help="danh sách thư mục video, ví dụ 1,2")
    parser.add_argument("--out", type=Path, default=OUT)
    args = parser.parse_args()

    wanted = {v.strip() for v in args.videos.split(",") if v.strip()}
    videos = sorted(DATA_DIR.glob("*/*.avi"), key=lambda p: int(p.parent.name))
    if wanted:
        videos = [v for v in videos if v.parent.name in wanted]
    if not videos:
        raise SystemExit(f"không thấy video trong {DATA_DIR}")

    results = []
    for video in videos:
        tags = read_tags(video.with_suffix(".tag"))
        result = run_video(video, tags, args.stride)
        results.append(result)
        print(json.dumps(result, ensure_ascii=False), flush=True)

    total_min = sum(r["duration_min"] for r in results)
    total_drowsy = sum(r["events"].get("DROWSINESS_ACUTE", 0) for r in results)
    frame = {k: sum(r["frame_level"][k] for r in results) for k in ("tp", "fp", "fn", "tn")}
    summary = {
        "dataset": "eyeblink8 (blinkingmatters.com, Fogelton & Benesova)",
        "stride": args.stride,
        "thresholds": {"ear": load_thresholds().ear_threshold, "eyes_closed_s": load_thresholds().eyes_closed_s},
        "videos": len(results),
        "total_minutes": round(total_min, 1),
        "blinks_annotated": sum(r["blinks_annotated"] for r in results),
        "blink_recall": round(sum(r["blinks_with_ear_dip"] for r in results) / max(sum(r["blinks_annotated"] for r in results), 1), 3),
        "face_rate": round(sum(r["face_rate"] * r["frames_processed"] for r in results) / max(sum(r["frames_processed"] for r in results), 1), 3),
        "frame_level": {**frame,
                        "recall": round(frame["tp"] / max(frame["tp"] + frame["fn"], 1), 3),
                        "fpr": round(frame["fp"] / max(frame["fp"] + frame["tn"], 1), 4)},
        "closure_latency_s": _latency_summary(results),
        "false_DROWSINESS_ACUTE": total_drowsy,
        "false_DROWSINESS_ACUTE_per_min": round(total_drowsy / total_min, 4) if total_min else None,
        "events_total": {k: sum(r["events"].get(k, 0) for r in results) for k in sorted({k for r in results for k in r["events"]})},
        "ms_per_frame_cpu": round(sum(r["ms_per_frame"] * r["frames_processed"] for r in results) / max(sum(r["frames_processed"] for r in results), 1), 1),
        "per_video": results,
    }
    args.out.write_text(json.dumps(summary, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps({k: v for k, v in summary.items() if k != "per_video"}, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
