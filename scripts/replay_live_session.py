# Phát lại telemetry phiên thử qua DriverPipeline; --pose-fallback bật thử nghiệm dự phòng pose.
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, ".")

from ai.perception.pose_tracker import PoseObservation
from ai.runtime.pipeline import DriverPipeline, FaceObservation, PhoneObservation
from ai.runtime.thresholds import load_thresholds


def main() -> None:
    parser = argparse.ArgumentParser(description="Phát lại telemetry một phiên thử DriverGuard.")
    parser.add_argument(
        "--session",
        type=Path,
        default=Path("docs/experiments/live_session.json"),
        help="Tệp phiên thử JSON.",
    )
    parser.add_argument(
        "--pose-fallback",
        action="store_true",
        help="Bật fallback pose cho lần phát lại này.",
    )
    args = parser.parse_args()

    with args.session.open(encoding="utf-8") as source:
        data = json.load(source)
    frames, marks, steps = data["frames"], data["marks"], data["steps"]
    bounds = [(mark["phase"], mark["t"]) for mark in marks]

    def phase_of(timestamp: float) -> str | None:
        phase = None
        for name, marked_at in bounds:
            if timestamp >= marked_at:
                phase = name
        return phase

    th = load_thresholds()
    th.use_pose_fallback = args.pose_fallback
    print(
        "ngưỡng: ear_fallback", th.ear_threshold,
        "| mar", th.mar_threshold,
        "| yaw", th.yaw_threshold,
        "| pitch", th.pitch_threshold,
        "| pose_fallback", th.use_pose_fallback,
    )
    pipe = DriverPipeline(th)
    start = bounds[0][1]
    ev_by_phase: dict[str | None, list[str]] = {}
    flags_by_phase: dict[str | None, set[str]] = {}
    for frame in frames:
        if frame["t"] < start:
            continue
        face = (
            FaceObservation(frame["ear"], frame["mar"], frame["yaw"], frame["pitch"], 0.0)
            if frame["face_detected"]
            else None
        )
        pose = None
        pose_data = frame.get("pose")
        if (
            args.pose_fallback
            and isinstance(pose_data, dict)
            and pose_data.get("person")
            and pose_data.get("yaw") is not None
            and pose_data.get("pitch") is not None
        ):
            pose = PoseObservation(
                keypoints=(),
                yaw_proxy=float(pose_data["yaw"]),
                pitch_proxy=float(pose_data["pitch"]),
                ear_asym=float(pose_data["ear_asym"] or 0.0),
                observed_at=float(frame["t"]),
            )
        tele, events = pipe.update(
            frame["t"],
            face,
            PhoneObservation(frame.get("phone_detected", False), False),
            pose,
        )
        phase = phase_of(frame["t"])
        for event in events:
            ev_by_phase.setdefault(phase, []).append(event["event_type"])
        for key in ("eyes_closed", "yawning", "looking_away", "looking_down"):
            if tele[key]:
                flags_by_phase.setdefault(phase, set()).add(key)

    baseline = pipe.ear_baseline
    print(
        "ear_baseline (từ 4 giây đầu):",
        round(baseline, 3) if baseline is not None else None,
        "-> ngưỡng nhắm mắt",
        round(pipe.ear_threshold, 3),
    )
    print(f'{"pha":12s} {"cờ":38s} sự kiện')
    for name, _, _ in steps:
        if name == "end":
            continue
        print(f'{name:12s} {str(sorted(flags_by_phase.get(name, []))):38s} {sorted(set(ev_by_phase.get(name, [])))}')


if __name__ == "__main__":
    main()
