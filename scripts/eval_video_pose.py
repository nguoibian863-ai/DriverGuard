"""Đánh giá offline pose fallback trên video công khai, theo thời gian video."""

from __future__ import annotations

import argparse
import csv
import json
import random
import sys
import time
from collections import Counter
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ai.perception.face_landmarks import FaceLandmarkTracker
from ai.perception.pose_tracker import PoseObservation, PoseTracker
from ai.runtime.pipeline import DriverPipeline, FaceObservation, PhoneObservation
from ai.runtime.thresholds import load_thresholds

DEFAULT_VIDEO_IDS = ("FD5ctXyExqc", "VPnBwC1fOJY", "lKIkpzwuaWs", "3psnER2oVUA")
DEFAULT_OUT_DIR = ROOT / "docs" / "experiments" / "web_video"
VIDEO_DIR = ROOT / "data" / "raw" / "web_videos"
RANDOM_SEED = 8002
PRIMARY_FLAGS = ("LOOKING_AWAY", "LOOKING_DOWN", "DRIVER_ABSENCE")
ALL_FLAGS = (
    "DROWSINESS_ACUTE",
    "YAWNING",
    "LOOKING_AWAY",
    "LOOKING_DOWN",
    "PHONE_USAGE",
    "DRIVER_ABSENCE",
)
TELEMETRY_FLAG_KEYS = {
    "DROWSINESS_ACUTE": "eyes_closed",
    "YAWNING": "yawning",
    "LOOKING_AWAY": "looking_away",
    "LOOKING_DOWN": "looking_down",
    "PHONE_USAGE": "phone_usage",
}
MAX_DIFF_SAMPLES = 20
MAX_NO_POSE_SAMPLES = 10
MAX_RANDOM_SAMPLES = 10
MAX_TOTAL_SAMPLES = 40


@dataclass
class SampleCandidate:
    frame_index: int
    t: float
    flags_a: dict[str, bool]
    flags_b: dict[str, bool]
    pose_keypoints: tuple[tuple[float, float, float], ...] | None
    category: str


class Reservoir:
    """Reservoir sampling với seed cố định, chỉ giữ metadata của tối đa N khung."""

    def __init__(self, capacity: int, rng: random.Random) -> None:
        self.capacity = capacity
        self.rng = rng
        self.seen = 0
        self.items: list[SampleCandidate] = []

    def add(self, item: SampleCandidate) -> None:
        self.seen += 1
        if len(self.items) < self.capacity:
            self.items.append(item)
            return
        slot = self.rng.randrange(self.seen)
        if slot < self.capacity:
            self.items[slot] = item


def _resolve_video(value: str) -> Path:
    candidate = Path(value)
    if candidate.is_file():
        return candidate.resolve()
    if candidate.suffix.lower() != ".mp4":
        candidate = VIDEO_DIR / f"{value}.mp4"
    elif not candidate.is_absolute():
        candidate = ROOT / candidate
    if not candidate.is_file():
        raise FileNotFoundError(f"Không tìm thấy video: {candidate}")
    return candidate.resolve()


def _flag_values(telemetry: dict[str, Any], pipeline: DriverPipeline) -> dict[str, bool]:
    values = {
        name: bool(telemetry.get(key, False))
        for name, key in TELEMETRY_FLAG_KEYS.items()
    }
    # DriverPipeline.update hiện không đưa DRIVER_ABSENCE vào telemetry. Đọc state
    # FSM sau update để lấy cờ ACTIVE đúng cùng cách các cờ còn lại được tạo ra.
    values["DRIVER_ABSENCE"] = pipeline.absence_fsm.state.name == "ACTIVE"
    return values


def _flag_label(flags: dict[str, bool]) -> str:
    active = [name for name in PRIMARY_FLAGS if flags.get(name, False)]
    return "+".join(active) if active else "NONE"


def _has_primary_difference(a: dict[str, bool], b: dict[str, bool]) -> bool:
    return any(a.get(name, False) != b.get(name, False) for name in PRIMARY_FLAGS)


def _select_spaced(
    candidates: list[SampleCandidate],
    limit: int,
    chosen_indices: set[int],
    fps: float,
    rng: random.Random,
) -> list[SampleCandidate]:
    pool = [item for item in candidates if item.frame_index not in chosen_indices]
    rng.shuffle(pool)
    selected: list[SampleCandidate] = []
    min_gap = max(1, int(np.ceil(fps)))
    for item in pool:
        if len(selected) >= limit:
            break
        if any(abs(item.frame_index - other) < min_gap for other in chosen_indices):
            continue
        selected.append(item)
        chosen_indices.add(item.frame_index)
    return selected


def _sample_candidates(
    diff_pool: list[SampleCandidate],
    no_pose_pool: list[SampleCandidate],
    random_pool: list[SampleCandidate],
    fps: float,
    rng: random.Random,
) -> list[SampleCandidate]:
    chosen_indices: set[int] = set()
    selected: list[SampleCandidate] = []
    for candidates, limit, category in (
        (diff_pool, MAX_DIFF_SAMPLES, "a_b_different"),
        (no_pose_pool, MAX_NO_POSE_SAMPLES, "face_missing_pose_missing"),
        (random_pool, MAX_RANDOM_SAMPLES, "random_control"),
    ):
        for item in _select_spaced(candidates, limit, chosen_indices, fps, rng):
            item.category = category
            selected.append(item)
    return sorted(selected[:MAX_TOTAL_SAMPLES], key=lambda item: item.frame_index)


def _draw_sample(
    frame_bgr: np.ndarray,
    sample: SampleCandidate,
    out_path: Path,
) -> bool:
    h, w = frame_bgr.shape[:2]
    scale = min(1.0, 640.0 / max(h, w))
    if scale < 1.0:
        frame = cv2.resize(
            frame_bgr,
            (max(1, int(round(w * scale))), max(1, int(round(h * scale)))),
            interpolation=cv2.INTER_AREA,
        )
    else:
        frame = frame_bgr.copy()

    def line(label: str, flags: dict[str, bool]) -> str:
        active = [name for name in PRIMARY_FLAGS if flags.get(name, False)]
        state = "+".join(active) if active else "NONE"
        return f"{label}: {state}"

    cv2.rectangle(frame, (0, 0), (min(frame.shape[1] - 1, 430), 48), (0, 0, 0), -1)
    cv2.putText(frame, line("A", sample.flags_a), (8, 20), cv2.FONT_HERSHEY_SIMPLEX, 0.48, (80, 230, 80), 1, cv2.LINE_AA)
    cv2.putText(frame, line("B", sample.flags_b), (8, 42), cv2.FONT_HERSHEY_SIMPLEX, 0.48, (80, 220, 255), 1, cv2.LINE_AA)

    points = sample.pose_keypoints or ()
    selected = {}
    for index, label, color in ((0, "nose", (0, 0, 255)), (5, "L shoulder", (255, 100, 0)), (6, "R shoulder", (0, 180, 255))):
        if index >= len(points):
            continue
        x, y, confidence = points[index]
        if confidence < 0.3:
            continue
        px, py = int(round(x * scale)), int(round(y * scale))
        selected[index] = (px, py)
        cv2.circle(frame, (px, py), 5, color, -1, cv2.LINE_AA)
        cv2.putText(frame, label, (px + 5, py - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.38, color, 1, cv2.LINE_AA)
    if 5 in selected and 6 in selected:
        cv2.line(frame, selected[5], selected[6], (0, 220, 255), 2, cv2.LINE_AA)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    return bool(cv2.imwrite(str(out_path), frame, [cv2.IMWRITE_JPEG_QUALITY, 82]))


def _render_samples(video_path: Path, samples: list[SampleCandidate], frame_dir: Path, video_id: str) -> list[dict[str, str]]:
    if not samples:
        return []
    wanted = {sample.frame_index: sample for sample in samples}
    last_wanted = max(wanted)
    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        raise RuntimeError(f"Không mở lại được video để xuất ảnh mẫu: {video_path}")
    saved: list[dict[str, str]] = []
    index = 0
    try:
        while index <= last_wanted:
            ok, frame = cap.read()
            if not ok:
                break
            sample = wanted.get(index)
            if sample is not None:
                flags_a = _flag_label(sample.flags_a)
                flags_b = _flag_label(sample.flags_b)
                file_name = f"{video_id}_t{sample.t:.1f}_{flags_a}-{flags_b}.jpg"
                target = frame_dir / file_name
                if _draw_sample(frame, sample, target):
                    saved.append({"file": str(target.as_posix()), "category": sample.category, "t": round(sample.t, 3)})
            index += 1
    finally:
        cap.release()
    return saved


def _empty_flag_counts() -> dict[str, dict[str, float | int]]:
    return {name: {"frames": 0, "seconds": 0.0} for name in ALL_FLAGS}


def process_video(
    video_path: Path,
    out_dir: Path,
    max_seconds: float | None,
    pose_every: int,
    face_tracker: FaceLandmarkTracker,
    pose_tracker: PoseTracker,
) -> dict[str, Any]:
    video_id = video_path.stem
    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        raise RuntimeError(f"Không mở được video: {video_path}")
    fps = float(cap.get(cv2.CAP_PROP_FPS))
    if not np.isfinite(fps) or fps <= 0:
        cap.release()
        raise RuntimeError(f"FPS không hợp lệ ({fps}) trong {video_path}")
    source_frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    source_duration_s = source_frame_count / fps if source_frame_count > 0 else None

    base = load_thresholds()
    pipe_a = DriverPipeline(replace(base, use_pose_fallback=False))
    pipe_b = DriverPipeline(replace(base, use_pose_fallback=True))
    calibration_done = {"A": None, "B": None}
    event_counts: dict[str, Counter[str]] = {"A": Counter(), "B": Counter()}
    flag_counts = {"A": _empty_flag_counts(), "B": _empty_flag_counts()}
    pre_cal_flags = {"A": _empty_flag_counts(), "B": _empty_flag_counts()}
    eligible_frames = 0
    pre_calibration_frames = 0
    eligible_face_missing = 0
    eligible_face_missing_pose_fresh = 0
    eligible_face_missing_pose_detected = 0
    difference_frames = 0
    difference_by_flag = Counter()
    processed_frames = 0
    last_pose: PoseObservation | None = None
    diff_pool: list[SampleCandidate] = []
    no_pose_pool: list[SampleCandidate] = []
    rng = random.Random(RANDOM_SEED + sum(ord(char) for char in video_id))
    diff_reservoir = Reservoir(160, rng)
    no_pose_reservoir = Reservoir(80, rng)
    random_reservoir = Reservoir(100, rng)
    csv_path = out_dir / f"{video_id}.csv"
    columns = [
        "frame_index", "t", "face_detected", "ear", "mar", "yaw", "pitch",
        "pose_person", "pose_fresh", "pose_yaw_rel", "pose_pitch_rel",
        "calibrated_A", "calibrated_B",
    ]
    for label in ("A", "B"):
        columns.extend(f"{label}_{name.lower()}" for name in ALL_FLAGS)
        columns.extend((f"{label}_risk_level", f"{label}_risk_score", f"{label}_events"))

    started = time.monotonic()
    with csv_path.open("w", newline="", encoding="utf-8-sig") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=columns)
        writer.writeheader()
        frame_index = 0
        while True:
            t = frame_index / fps
            if max_seconds is not None and t >= max_seconds:
                break
            ok, frame_bgr = cap.read()
            if not ok:
                break

            if frame_index % pose_every == 0:
                detected_pose = pose_tracker.detect(frame_bgr)
                last_pose = replace(detected_pose, observed_at=t) if detected_pose is not None else None

            rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
            face, _face_box, _landmarks = face_tracker.process(rgb, t)
            pose_fresh = last_pose is not None and last_pose.observed_at is not None and 0.0 <= t - last_pose.observed_at <= base.pose_max_age_s
            phone = PhoneObservation()
            tele_a, events_a = pipe_a.update(t, face, phone, last_pose)
            tele_b, events_b = pipe_b.update(t, face, phone, last_pose)
            flags_a = _flag_values(tele_a, pipe_a)
            flags_b = _flag_values(tele_b, pipe_b)
            if tele_a["calibrated"] and calibration_done["A"] is None:
                calibration_done["A"] = t
            if tele_b["calibrated"] and calibration_done["B"] is None:
                calibration_done["B"] = t

            calibrated_both = bool(tele_a["calibrated"] and tele_b["calibrated"])
            if calibrated_both:
                eligible_frames += 1
                if not tele_a["face_detected"]:
                    eligible_face_missing += 1
                    if pose_fresh:
                        eligible_face_missing_pose_fresh += 1
                    if last_pose is not None:
                        eligible_face_missing_pose_detected += 1
                changed = _has_primary_difference(flags_a, flags_b)
                if changed:
                    difference_frames += 1
                    for name in PRIMARY_FLAGS:
                        if flags_a[name] != flags_b[name]:
                            difference_by_flag[name] += 1
                    diff_reservoir.add(SampleCandidate(
                        frame_index, t, flags_a.copy(), flags_b.copy(),
                        last_pose.keypoints if last_pose is not None else None, "a_b_different",
                    ))
                if not tele_a["face_detected"] and not pose_fresh:
                    no_pose_reservoir.add(SampleCandidate(
                        frame_index, t, flags_a.copy(), flags_b.copy(),
                        last_pose.keypoints if last_pose is not None else None, "face_missing_pose_missing",
                    ))
                random_reservoir.add(SampleCandidate(
                    frame_index, t, flags_a.copy(), flags_b.copy(),
                    last_pose.keypoints if last_pose is not None else None, "random_control",
                ))
                for label, flags, events in (("A", flags_a, events_a), ("B", flags_b, events_b)):
                    for name in ALL_FLAGS:
                        if flags[name]:
                            flag_counts[label][name]["frames"] += 1
                            flag_counts[label][name]["seconds"] += 1.0 / fps
                    for event in events:
                        event_counts[label][event["event_type"]] += 1
            else:
                pre_calibration_frames += 1
                for label, flags in (("A", flags_a), ("B", flags_b)):
                    for name in ALL_FLAGS:
                        if flags[name]:
                            pre_cal_flags[label][name]["frames"] += 1
                            pre_cal_flags[label][name]["seconds"] += 1.0 / fps

            pose_data = tele_b["pose"]
            row: dict[str, Any] = {
                "frame_index": frame_index,
                "t": f"{t:.6f}",
                "face_detected": bool(tele_a["face_detected"]),
                "ear": tele_a["ear"],
                "mar": tele_a["mar"],
                "yaw": tele_a["yaw"],
                "pitch": tele_a["pitch"],
                "pose_person": bool(pose_data["person"]),
                "pose_fresh": bool(pose_fresh),
                "pose_yaw_rel": pose_data["yaw_rel"],
                "pose_pitch_rel": pose_data["pitch_rel"],
                "calibrated_A": bool(tele_a["calibrated"]),
                "calibrated_B": bool(tele_b["calibrated"]),
            }
            for label, telemetry, flags, events in (
                ("A", tele_a, flags_a, events_a), ("B", tele_b, flags_b, events_b)
            ):
                for name in ALL_FLAGS:
                    row[f"{label}_{name.lower()}"] = flags[name]
                row[f"{label}_risk_level"] = telemetry["risk_level"]
                row[f"{label}_risk_score"] = telemetry["risk_score"]
                row[f"{label}_events"] = "|".join(event["event_type"] for event in events)
            writer.writerow(row)

            frame_index += 1
            processed_frames += 1
            if processed_frames % 500 == 0:
                elapsed = time.monotonic() - started
                print(f"[{video_id}] {processed_frames} khung, {t:.1f}s video, {processed_frames / max(elapsed, 1e-6):.1f} khung/s", flush=True)

    cap.release()
    processed_duration_s = processed_frames / fps
    if max_seconds is not None and source_duration_s is not None:
        truncated = max_seconds < source_duration_s
    else:
        truncated = False
    selected = _sample_candidates(
        diff_reservoir.items,
        no_pose_reservoir.items,
        random_reservoir.items,
        fps,
        rng,
    )
    frame_dir = out_dir / "frames" / video_id
    saved_samples = _render_samples(video_path, selected, frame_dir, video_id)

    def seconds(value: int) -> float:
        return round(value / fps, 3)

    notes = [
        "Video không có nhãn chuẩn; các số liệu là số đo telemetry, không xác nhận đúng/sai của cờ.",
        "Thống kê chính chỉ gồm khung sau khi cả A và B đã hiệu chuẩn; CSV chứa cả khung trước đó.",
    ]
    if video_id == "3psnER2oVUA":
        notes.append(
            "Clip montage nhiều cảnh; các số đo tổng hợp trên toàn clip có thể trộn nhiều người/cảnh "
            "và không nên quy kết cho một tài xế hay một cảnh cụ thể."
        )

    summary = {
        "video_id": video_id,
        "source": str(video_path.relative_to(ROOT).as_posix()) if video_path.is_relative_to(ROOT) else str(video_path),
        "source_frame_count": source_frame_count,
        "processed_frames": processed_frames,
        "fps": round(fps, 6),
        "source_duration_s": round(source_duration_s, 3) if source_duration_s is not None else None,
        "processed_duration_s": round(processed_duration_s, 3),
        "truncated_by_max_seconds": truncated,
        "calibration": {
            "calibration_s_threshold": base.calibration_s,
            "completed_at_s_A": round(calibration_done["A"], 6) if calibration_done["A"] is not None else None,
            "completed_at_s_B": round(calibration_done["B"], 6) if calibration_done["B"] is not None else None,
            "eligible_when_both_calibrated": True,
        },
        "main_statistics_after_both_calibrated": {
            "eligible_frames": eligible_frames,
            "face_missing_frames": eligible_face_missing,
            "face_missing_rate": round(eligible_face_missing / eligible_frames, 6) if eligible_frames else None,
            "pose_fresh_person_frames_when_face_missing": eligible_face_missing_pose_fresh,
            "pose_fresh_person_rate_when_face_missing": round(eligible_face_missing_pose_fresh / eligible_face_missing, 6) if eligible_face_missing else None,
            "pose_observation_frames_when_face_missing": eligible_face_missing_pose_detected,
            "flags": {
                label: {
                    name: {"frames": int(values["frames"]), "seconds": round(float(values["seconds"]), 3)}
                    for name, values in per_flag.items()
                }
                for label, per_flag in flag_counts.items()
            },
            "a_b_different_frames": difference_frames,
            "a_b_different_rate": round(difference_frames / eligible_frames, 6) if eligible_frames else None,
            "different_frames_by_flag": dict(difference_by_flag),
            "events_by_type": {label: dict(sorted(counter.items())) for label, counter in event_counts.items()},
        },
        "pre_calibration_excluded_from_main_statistics": {
            "frames": pre_calibration_frames,
            "seconds": seconds(pre_calibration_frames),
            "flags": {
                label: {
                    name: {"frames": int(values["frames"]), "seconds": round(float(values["seconds"]), 3)}
                    for name, values in per_flag.items()
                }
                for label, per_flag in pre_cal_flags.items()
            },
        },
        "driver_absence_source": "DriverPipeline.update không xuất cờ này trong telemetry; lấy AlertState ACTIVE từ absence_fsm.state sau update.",
        "pose_every_frames": pose_every,
        "samples": {
            "saved_count": len(saved_samples),
            "by_category": dict(sorted(Counter(sample["category"] for sample in saved_samples).items())),
            "files": saved_samples,
        },
        "notes": notes,
    }
    return summary


def _print_table(summaries: list[dict[str, Any]]) -> None:
    headers = ("video", "frames", "fps", "duration", "face lost", "pose|face lost", "diff A/B", "samples")
    rows = []
    for item in summaries:
        main = item["main_statistics_after_both_calibrated"]
        rows.append((
            item["video_id"],
            str(item["processed_frames"]),
            f"{item['fps']:.2f}",
            f"{item['processed_duration_s']:.1f}s",
            f"{main['face_missing_frames']}/{main['eligible_frames']} ({main['face_missing_rate'] if main['face_missing_rate'] is not None else 'n/a'})",
            f"{main['pose_fresh_person_frames_when_face_missing']}/{main['face_missing_frames']} ({main['pose_fresh_person_rate_when_face_missing'] if main['pose_fresh_person_rate_when_face_missing'] is not None else 'n/a'})",
            str(main["a_b_different_frames"]),
            str(item["samples"]["saved_count"]),
        ))
    widths = [max(len(headers[i]), *(len(row[i]) for row in rows)) for i in range(len(headers))]
    print(" | ".join(headers[i].ljust(widths[i]) for i in range(len(headers))))
    print("-+-".join("-" * width for width in widths))
    for row in rows:
        print(" | ".join(row[i].ljust(widths[i]) for i in range(len(headers))))

    print("\nActive flags after calibration: frames (seconds); events are emitted counts by type")
    detail_rows = []
    for item in summaries:
        main = item["main_statistics_after_both_calibrated"]
        side_text = {}
        for side in ("A", "B"):
            flags = main["flags"][side]
            flag_text = ", ".join(
                f"{name} {flags[name]['frames']} ({flags[name]['seconds']:.3f}s)"
                for name in PRIMARY_FLAGS
            )
            events = main["events_by_type"][side]
            event_text = ", ".join(f"{name} {count}" for name, count in sorted(events.items())) or "ninguna"
            side_text[side] = (flag_text, event_text)
        detail_rows.append((item["video_id"], side_text["A"][0], side_text["B"][0], side_text["A"][1], side_text["B"][1]))
    detail_headers = ("video", "A flags", "B flags", "events A", "events B")
    detail_widths = [max(len(detail_headers[i]), *(len(row[i]) for row in detail_rows)) for i in range(len(detail_headers))]
    print(" | ".join(detail_headers[i].ljust(detail_widths[i]) for i in range(len(detail_headers))))
    print("-+-".join("-" * width for width in detail_widths))
    for row in detail_rows:
        print(" | ".join(row[i].ljust(detail_widths[i]) for i in range(len(detail_headers))))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Đánh giá offline pose fallback trên video web.")
    parser.add_argument("--video", action="append", help="ID video hoặc đường dẫn; có thể lặp lại. Mặc định chạy cả bốn video.")
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR, help="Thư mục đầu ra.")
    parser.add_argument("--max-seconds", type=float, default=None, help="Giới hạn thời lượng video để chạy thử.")
    parser.add_argument("--pose-every", type=int, default=1, help="Số khung giữa hai lần chạy PoseTracker.")
    args = parser.parse_args()
    if args.max_seconds is not None and args.max_seconds <= 0:
        parser.error("--max-seconds phải lớn hơn 0")
    if args.pose_every < 1:
        parser.error("--pose-every phải từ 1 trở lên")
    return args


def main() -> None:
    args = parse_args()
    video_values = args.video or list(DEFAULT_VIDEO_IDS)
    videos = [_resolve_video(value) for value in video_values]
    out_dir = args.out_dir if args.out_dir.is_absolute() else ROOT / args.out_dir
    out_dir.mkdir(parents=True, exist_ok=True)

    face_tracker = FaceLandmarkTracker()
    try:
        pose_tracker = PoseTracker()
    except Exception:
        face_tracker.close()
        raise
    summaries: list[dict[str, Any]] = []
    try:
        for video_path in videos:
            print(f"Bắt đầu {video_path.stem}: {video_path}", flush=True)
            item = process_video(video_path, out_dir, args.max_seconds, args.pose_every, face_tracker, pose_tracker)
            summaries.append(item)
            main_stats = item["main_statistics_after_both_calibrated"]
            print(
                f"Hoàn tất {video_path.stem}: {item['processed_frames']} khung, "
                f"hiệu chuẩn A/B={item['calibration']['completed_at_s_A']}/{item['calibration']['completed_at_s_B']} s, "
                f"khung khác cờ={main_stats['a_b_different_frames']}, ảnh={item['samples']['saved_count']}",
                flush=True,
            )
    finally:
        face_tracker.close()

    payload = {
        "experiment": "EXP-008",
        "evaluation": "AI-002 pose fallback; synchronous offline replay with t = frame_index / fps",
        "pose_every_frames": args.pose_every,
        "max_seconds": args.max_seconds,
        "random_seed": RANDOM_SEED,
        "videos": summaries,
    }
    summary_path = out_dir / "summary.json"
    summary_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    _print_table(summaries)
    print(f"Đã ghi summary: {summary_path}")


if __name__ == "__main__":
    main()
