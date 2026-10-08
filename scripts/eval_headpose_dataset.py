"""Đánh giá MediaPipe và pose fallback trên Pointing'04 dạng parquet."""

from __future__ import annotations

import argparse
import csv
import json
import math
import sys
from pathlib import Path
from statistics import median
from typing import Any, Iterable

import cv2
import numpy as np
import pyarrow.parquet as pq

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ai.perception.face_landmarks import FaceLandmarkTracker
from ai.perception.pose_tracker import PoseTracker, compute_pose_features
from ai.runtime.thresholds import load_thresholds

DATA_DIR = ROOT / "data" / "raw" / "headpose"
OUT_DIR = ROOT / "docs" / "experiments" / "headpose"
EXPECTED_ANGLES = tuple(range(-90, 91, 15))
POSE_YAW_SWEEP = (0.20, 0.25, 0.30, 0.35, 0.40, 0.50)

PER_IMAGE_COLUMNS = (
    "image_index",
    "split",
    "row_in_split",
    "subject_id",
    "gt_tilt_a_deg",
    "gt_pan_b_deg",
    "face_detected",
    "face_yaw_deg",
    "face_pitch_raw_deg",
    "face_pitch_signed_deg",
    "relative_yaw_deg",
    "relative_pitch_signed_deg",
    "pose_usable",
    "pose_features_valid",
    "yaw_proxy",
    "pitch_proxy",
    "relative_pose_yaw",
    "relative_pose_pitch",
    "decode_error",
)


def _average_ranks(values: list[float]) -> list[float]:
    ordered = sorted(enumerate(values), key=lambda pair: pair[1])
    ranks = [0.0] * len(values)
    i = 0
    while i < len(ordered):
        j = i + 1
        while j < len(ordered) and ordered[j][1] == ordered[i][1]:
            j += 1
        average_rank = ((i + 1) + j) / 2.0
        for k in range(i, j):
            ranks[ordered[k][0]] = average_rank
        i = j
    return ranks


def spearman(x: Iterable[float], y: Iterable[float]) -> float | None:
    """Spearman rho với average-rank khi có ties, không cần scipy."""
    pairs = [(float(a), float(b)) for a, b in zip(x, y) if math.isfinite(float(a)) and math.isfinite(float(b))]
    if len(pairs) < 2:
        return None
    rx = _average_ranks([a for a, _ in pairs])
    ry = _average_ranks([b for _, b in pairs])
    mx = sum(rx) / len(rx)
    my = sum(ry) / len(ry)
    cov = sum((a - mx) * (b - my) for a, b in zip(rx, ry))
    sx = math.sqrt(sum((a - mx) ** 2 for a in rx))
    sy = math.sqrt(sum((b - my) ** 2 for b in ry))
    if sx == 0.0 or sy == 0.0:
        return None
    return cov / (sx * sy)


def _rounded(value: float | None, digits: int = 6) -> float | None:
    return round(value, digits) if value is not None and math.isfinite(value) else None


def _rate(numerator: int, denominator: int) -> float | None:
    return _rounded(numerator / denominator) if denominator else None


def _binary_metrics(labels: list[bool], predictions: list[bool]) -> dict[str, int | float | None]:
    tp = sum(label and pred for label, pred in zip(labels, predictions))
    fp = sum((not label) and pred for label, pred in zip(labels, predictions))
    fn = sum(label and (not pred) for label, pred in zip(labels, predictions))
    tn = sum((not label) and (not pred) for label, pred in zip(labels, predictions))
    precision = _rate(tp, tp + fp)
    recall = _rate(tp, tp + fn)
    f1 = _rounded(2 * tp / (2 * tp + fp + fn)) if (2 * tp + fp + fn) else None
    fpr = _rate(fp, fp + tn)
    return {
        "tp": tp,
        "fp": fp,
        "fn": fn,
        "tn": tn,
        "precision": precision,
        "recall": recall,
        "f1": f1,
        "fpr": fpr,
    }


def _mean_or_none(values: list[float]) -> float | None:
    return _rounded(median(values)) if values else None


def _compute_bin_stats(rows: list[dict[str, Any]]) -> dict[str, Any]:
    face_rows = [row for row in rows if row["face_detected"]]
    pose_rows = [row for row in rows if row["pose_usable"]]
    errors = [
        abs(row["relative_yaw_deg"] - row["gt_pan_b_deg"])
        for row in face_rows
        if row["relative_yaw_deg"] is not None
    ]
    return {
        "n_images": len(rows),
        "face_detected_n": len(face_rows),
        "face_detected_rate": _rate(len(face_rows), len(rows)),
        "pose_usable_n": len(pose_rows),
        "pose_usable_rate": _rate(len(pose_rows), len(rows)),
        "both_missing_n": sum(not row["face_detected"] and not row["pose_usable"] for row in rows),
        "both_missing_rate": _rate(
            sum(not row["face_detected"] and not row["pose_usable"] for row in rows), len(rows)
        ),
        "median_abs_relative_mp_yaw_error_deg": _mean_or_none(errors),
        "pose_yaw_spearman_vs_gt_pan": _rounded(
            spearman(
                [row["yaw_proxy"] for row in pose_rows],
                [row["gt_pan_b_deg"] for row in pose_rows],
            )
        ),
    }


def _write_per_image(rows: list[dict[str, Any]], path: Path, baselines: dict[str, float | None]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=PER_IMAGE_COLUMNS)
        writer.writeheader()
        for row in rows:
            relative_yaw = (
                row["face_yaw_deg"] - baselines["face_yaw_deg"]
                if row["face_detected"] and baselines["face_yaw_deg"] is not None
                else None
            )
            relative_pitch = (
                row["face_pitch_signed_deg"] - baselines["face_pitch_signed_deg"]
                if row["face_detected"] and baselines["face_pitch_signed_deg"] is not None
                else None
            )
            relative_pose_yaw = (
                row["yaw_proxy"] - baselines["yaw_proxy"]
                if row["pose_usable"] and baselines["yaw_proxy"] is not None
                else None
            )
            relative_pose_pitch = (
                row["pitch_proxy"] - baselines["pitch_proxy"]
                if row["pose_usable"] and baselines["pitch_proxy"] is not None
                else None
            )
            writer.writerow({
                **{key: row.get(key) for key in PER_IMAGE_COLUMNS},
                "relative_yaw_deg": relative_yaw,
                "relative_pitch_signed_deg": relative_pitch,
                "relative_pose_yaw": relative_pose_yaw,
                "relative_pose_pitch": relative_pose_pitch,
            })


def _classification_results(
    rows: list[dict[str, Any]],
    yaw_threshold: float,
    pitch_threshold: float,
    pose_yaw_ratio: float,
    pose_pitch_ratio: float,
    positive_tilt_is_down: bool,
) -> dict[str, Any]:
    labels = {
        "looking_away_30": [abs(row["gt_pan_b_deg"]) >= 30 for row in rows],
        "looking_away_45": [abs(row["gt_pan_b_deg"]) >= 45 for row in rows],
        "looking_down_30": [
            (row["gt_tilt_a_deg"] if positive_tilt_is_down else -row["gt_tilt_a_deg"]) >= 30
            for row in rows
        ],
    }
    predictors: dict[str, dict[str, list[bool]]] = {}
    for name in labels:
        a: list[bool] = []
        pose_only_yaw: list[bool] = []
        b: list[bool] = []
        pose_only_pitch: list[bool] = []
        for row in rows:
            face_prediction = False
            if row["face_detected"]:
                if name.startswith("looking_away") and row["relative_yaw_deg"] is not None:
                    face_prediction = abs(row["relative_yaw_deg"]) >= yaw_threshold
                elif name == "looking_down_30" and row["relative_pitch_signed_deg"] is not None:
                    face_prediction = row["relative_pitch_signed_deg"] >= pitch_threshold
            pose_yaw_prediction = (
                row["pose_usable"]
                and row["relative_pose_yaw"] is not None
                and abs(row["relative_pose_yaw"]) >= pose_yaw_ratio
            )
            pose_pitch_prediction = (
                row["pose_usable"]
                and row["relative_pose_pitch"] is not None
                and row["relative_pose_pitch"] >= pose_pitch_ratio
            )
            pose_prediction = pose_yaw_prediction if name.startswith("looking_away") else pose_pitch_prediction
            a.append(face_prediction)
            pose_only_yaw.append(pose_yaw_prediction)
            pose_only_pitch.append(pose_pitch_prediction)
            b.append(face_prediction or (not row["face_detected"] and pose_prediction))
        predictors[name] = {
            "A_media_pipe_only": a,
            "B_face_plus_pose_fallback": b,
            "pose_only": pose_only_yaw if name.startswith("looking_away") else pose_only_pitch,
        }
    return {
        name: {system: _binary_metrics(labels[name], predictions) for system, predictions in systems.items()}
        for name, systems in predictors.items()
    }


def _threshold_sweep(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    labels30 = [abs(row["gt_pan_b_deg"]) >= 30 for row in rows]
    labels45 = [abs(row["gt_pan_b_deg"]) >= 45 for row in rows]
    yaw_threshold = load_thresholds().yaw_threshold
    results = []
    for threshold in POSE_YAW_SWEEP:
        pose_preds = [
            row["pose_usable"] and row["relative_pose_yaw"] is not None
            and abs(row["relative_pose_yaw"]) >= threshold
            for row in rows
        ]
        b_preds = [
            (row["face_detected"] and row["relative_yaw_deg"] is not None
             and abs(row["relative_yaw_deg"]) >= yaw_threshold)
            or (not row["face_detected"] and pose_pred)
            for row, pose_pred in zip(rows, pose_preds)
        ]
        results.append({
            "pose_yaw_ratio": threshold,
            "looking_away_30": {
                "pose_only": _binary_metrics(labels30, pose_preds),
                "B_face_plus_pose_fallback": _binary_metrics(labels30, b_preds),
            },
            "looking_away_45": {
                "pose_only": _binary_metrics(labels45, pose_preds),
                "B_face_plus_pose_fallback": _binary_metrics(labels45, b_preds),
            },
        })
    return results


def _write_bins(rows: list[dict[str, Any]], path: Path) -> dict[str, Any]:
    fields = (
        "dimension", "pan_bin_deg", "tilt_bin_deg", "n_images",
        "face_detected_n", "face_detected_rate", "pose_usable_n", "pose_usable_rate",
        "both_missing_n", "both_missing_rate", "median_abs_relative_mp_yaw_error_deg",
        "pose_yaw_spearman_vs_gt_pan",
    )
    records: list[dict[str, Any]] = []
    overall = _compute_bin_stats(rows)
    records.append({"dimension": "overall", **overall})
    for pan in EXPECTED_ANGLES:
        stats = _compute_bin_stats([row for row in rows if row["gt_pan_b_deg"] == pan])
        records.append({"dimension": "pan", "pan_bin_deg": pan, **stats})
    for tilt in EXPECTED_ANGLES:
        stats = _compute_bin_stats([row for row in rows if row["gt_tilt_a_deg"] == tilt])
        records.append({"dimension": "tilt", "tilt_bin_deg": tilt, **stats})
    for pan in EXPECTED_ANGLES:
        for tilt in EXPECTED_ANGLES:
            selected = [
                row for row in rows
                if row["gt_pan_b_deg"] == pan and row["gt_tilt_a_deg"] == tilt
            ]
            stats = _compute_bin_stats(selected)
            records.append({"dimension": "pan_x_tilt_detection", "pan_bin_deg": pan, "tilt_bin_deg": tilt, **stats})
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(records)
    return overall


def _evaluate(limit: int | None) -> dict[str, Any]:
    files = sorted(DATA_DIR.glob("train-*.parquet"))
    if not files:
        raise FileNotFoundError(f"Không tìm thấy parquet tại {DATA_DIR}")

    thresholds = load_thresholds()
    face_tracker = FaceLandmarkTracker()
    try:
        pose_tracker = PoseTracker()
    except Exception:
        face_tracker.close()
        raise

    rows: list[dict[str, Any]] = []
    split_counts: dict[str, int] = {}
    decode_errors = 0
    next_timestamp_s = 0.0
    try:
        for parquet_path in files:
            parquet_file = pq.ParquetFile(parquet_path)
            split = parquet_path.stem
            split_count = 0
            for batch in parquet_file.iter_batches(batch_size=4, columns=["x", "y"]):
                images = batch.column("x").to_pylist()
                targets = batch.column("y").to_pylist()
                for image_obj, target in zip(images, targets):
                    if limit is not None and len(rows) >= limit:
                        break
                    if not isinstance(target, list) or len(target) != 2:
                        raise ValueError(f"Nhãn không hợp lệ tại {split} hàng {split_count}: {target!r}")
                    tilt_a, pan_b = int(target[0]), int(target[1])
                    if tilt_a not in EXPECTED_ANGLES or pan_b not in EXPECTED_ANGLES:
                        raise ValueError(f"Nhãn ngoài lưới 15° tại {split} hàng {split_count}: {target!r}")

                    image_bytes = image_obj.get("bytes") if isinstance(image_obj, dict) else None
                    if not image_bytes:
                        raise ValueError(f"Thiếu bytes ảnh tại {split} hàng {split_count}")
                    encoded = np.frombuffer(image_bytes, dtype=np.uint8)
                    frame_bgr = cv2.imdecode(encoded, cv2.IMREAD_COLOR)
                    decode_error = frame_bgr is None
                    if decode_error:
                        decode_errors += 1
                        rgb = None
                    else:
                        rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)

                    # VIDEO mode như worker; mỗi ảnh tĩnh nhận timestamp giả tăng đơn điệu 1/30 s.
                    next_timestamp_s += 1.0 / 30.0
                    face = None
                    if rgb is not None:
                        face, _box, _landmarks = face_tracker.process(rgb, next_timestamp_s)
                    pose_observation = pose_tracker.detect(frame_bgr) if frame_bgr is not None else None
                    pose_features = (
                        compute_pose_features(pose_observation.keypoints)
                        if pose_observation is not None else None
                    )
                    pose_valid = pose_features is not None
                    face_pitch_raw = float(face.pitch) if face is not None else None
                    row = {
                        "image_index": len(rows),
                        "split": split,
                        "row_in_split": split_count,
                        "subject_id": "",
                        "gt_tilt_a_deg": tilt_a,
                        "gt_pan_b_deg": pan_b,
                        "face_detected": face is not None,
                        "face_yaw_deg": float(face.yaw) if face is not None else None,
                        "face_pitch_raw_deg": face_pitch_raw,
                        "face_pitch_signed_deg": face_pitch_raw * thresholds.pitch_sign if face_pitch_raw is not None else None,
                        "relative_yaw_deg": None,
                        "relative_pitch_signed_deg": None,
                        "pose_usable": pose_valid,
                        "pose_features_valid": pose_valid,
                        "yaw_proxy": float(pose_observation.yaw_proxy) if pose_valid else None,
                        "pitch_proxy": float(pose_observation.pitch_proxy) if pose_valid else None,
                        "relative_pose_yaw": None,
                        "relative_pose_pitch": None,
                        "decode_error": decode_error,
                    }
                    rows.append(row)
                    split_count += 1
                    if len(rows) % 100 == 0:
                        print(f"Đã xử lý {len(rows)} ảnh...", flush=True)
                if limit is not None and len(rows) >= limit:
                    break
            split_counts[split] = split_count
            if limit is not None and len(rows) >= limit:
                break
    finally:
        face_tracker.close()

    neutral_rows = [row for row in rows if row["gt_tilt_a_deg"] == 0 and row["gt_pan_b_deg"] == 0]
    neutral_face = [row for row in neutral_rows if row["face_detected"]]
    neutral_pose = [row for row in neutral_rows if row["pose_usable"]]
    baselines: dict[str, float | None] = {
        "face_yaw_deg": median([row["face_yaw_deg"] for row in neutral_face]) if neutral_face else None,
        "face_pitch_signed_deg": median([row["face_pitch_signed_deg"] for row in neutral_face]) if neutral_face else None,
        "yaw_proxy": median([row["yaw_proxy"] for row in neutral_pose]) if neutral_pose else None,
        "pitch_proxy": median([row["pitch_proxy"] for row in neutral_pose]) if neutral_pose else None,
    }
    for row in rows:
        if row["face_detected"] and baselines["face_yaw_deg"] is not None:
            row["relative_yaw_deg"] = row["face_yaw_deg"] - baselines["face_yaw_deg"]
            row["relative_pitch_signed_deg"] = row["face_pitch_signed_deg"] - baselines["face_pitch_signed_deg"]
        if row["pose_usable"] and baselines["yaw_proxy"] is not None:
            row["relative_pose_yaw"] = row["yaw_proxy"] - baselines["yaw_proxy"]
            row["relative_pose_pitch"] = row["pitch_proxy"] - baselines["pitch_proxy"]

    face_rows = [row for row in rows if row["face_detected"]]
    face_pose_rows = [row for row in rows if row["face_detected"] and row["pose_usable"]]
    rho_mp_raw = spearman(
        [row["gt_tilt_a_deg"] for row in face_rows],
        [row["face_pitch_raw_deg"] for row in face_rows],
    )
    rho_mp_signed = spearman(
        [row["gt_tilt_a_deg"] for row in face_rows],
        [row["face_pitch_signed_deg"] for row in face_rows],
    )
    rho_pose = spearman(
        [row["gt_tilt_a_deg"] for row in face_pose_rows],
        [row["pitch_proxy"] for row in face_pose_rows],
    )
    if rho_pose is not None and rho_pose != 0:
        positive_tilt_is_down = rho_pose > 0
        direction_basis = "pose_pitch_proxy on images where both face and pose are usable"
    elif rho_mp_signed is not None and rho_mp_signed != 0:
        positive_tilt_is_down = rho_mp_signed > 0
        direction_basis = "MediaPipe pitch after configured pitch_sign; pose correlation unavailable/zero"
    else:
        positive_tilt_is_down = True
        direction_basis = "undetermined; conventional positive tilt fallback used only to keep metrics defined"

    _write_per_image(rows, OUT_DIR / "per_image.csv", baselines)
    bins_overall = _write_bins(rows, OUT_DIR / "bins.csv")
    classifications = _classification_results(
        rows,
        yaw_threshold=thresholds.yaw_threshold,
        pitch_threshold=thresholds.pitch_threshold,
        pose_yaw_ratio=thresholds.pose_yaw_ratio,
        pose_pitch_ratio=thresholds.pose_pitch_ratio,
        positive_tilt_is_down=positive_tilt_is_down,
    )
    sweep = _threshold_sweep(rows)

    n = len(rows)
    face_count = sum(row["face_detected"] for row in rows)
    pose_count = sum(row["pose_usable"] for row in rows)
    both_missing = sum(not row["face_detected"] and not row["pose_usable"] for row in rows)
    summary: dict[str, Any] = {
        "experiment": "EXP-010",
        "dataset": "HuggingFace StevenLe456/head-pose (Pointing'04)",
        "data_files": [path.relative_to(ROOT).as_posix() for path in files],
        "is_complete_dataset_run": limit is None,
        "limit": limit,
        "n_images_processed": n,
        "n_images_expected": sum(pq.ParquetFile(path).metadata.num_rows for path in files),
        "images_by_split": split_counts,
        "decode_errors": decode_errors,
        "angle_grid_deg": {"expected": list(EXPECTED_ANGLES), "tilt_values_present": sorted({r["gt_tilt_a_deg"] for r in rows}), "pan_values_present": sorted({r["gt_pan_b_deg"] for r in rows})},
        "detections": {
            "face_detected_n": face_count,
            "face_detected_rate": _rate(face_count, n),
            "pose_usable_n": pose_count,
            "pose_usable_rate": _rate(pose_count, n),
            "both_missing_n": both_missing,
            "both_missing_rate": _rate(both_missing, n),
        },
        "neutral_baseline_gt_tilt_0_pan_0": {
            "neutral_images_n": len(neutral_rows),
            "face_observed_n": len(neutral_face),
            "pose_usable_n": len(neutral_pose),
            "median": baselines,
        },
        "tilt_direction_empirical": {
            "pitch_sign_from_thresholds_yaml": thresholds.pitch_sign,
            "spearman_gt_tilt_vs_mediapipe_pitch_raw_face_visible": {"n": len(face_rows), "rho": _rounded(rho_mp_raw)},
            "spearman_gt_tilt_vs_mediapipe_pitch_signed_face_visible": {"n": len(face_rows), "rho": _rounded(rho_mp_signed)},
            "spearman_gt_tilt_vs_pose_pitch_proxy_face_visible_and_pose_usable": {"n": len(face_pose_rows), "rho": _rounded(rho_pose)},
            "positive_tilt_direction": "down" if positive_tilt_is_down else "up",
            "down_label_rule": "gt_tilt_a_deg >= 30" if positive_tilt_is_down else "gt_tilt_a_deg <= -30",
            "direction_basis": direction_basis,
        },
        "thresholds_read_without_modification": {
            "yaw_threshold_deg": thresholds.yaw_threshold,
            "pitch_threshold_deg": thresholds.pitch_threshold,
            "pitch_sign": thresholds.pitch_sign,
            "pose_yaw_ratio": thresholds.pose_yaw_ratio,
            "pose_pitch_ratio": thresholds.pose_pitch_ratio,
            "yaml_use_pose_fallback": thresholds.use_pose_fallback,
        },
        "overall_bin_metrics": bins_overall,
        "classifications": classifications,
        "pose_yaw_ratio_sweep": sweep,
        "method": {
            "image_iteration": "PyArrow ParquetFile.iter_batches(batch_size=4, columns=['x','y']); decode and infer one image at a time; no pandas and no full-image dataset in memory.",
            "face_tracker": "One FaceLandmarkTracker in VIDEO mode, matching the worker API; synthetic timestamps increase monotonically by 1/30 second across all parquet rows.",
            "pose_tracker": "PoseTracker.detect called once per decoded source image with the BGR frame, as in the worker; pose usable only when detect returns an observation and compute_pose_features(keypoints) is not None.",
            "relative_values": "MediaPipe pitch is multiplied by yaml pitch_sign before subtracting the GT-neutral median. Pose pitch_proxy is not sign-multiplied, matching pipeline.py where positive nose y is down. All four relative values subtract the corresponding median from usable GT (tilt=0, pan=0) images.",
            "classification": "A is MediaPipe only; missing face predicts false. B adds pose only when face is missing. Pose-only predicts from pose on every usable image. Per-image flags are instantaneous threshold comparisons; temporal FSM durations are not applied.",
            "subject_split": "Not available: x.path is null for all rows; repeated five-row label runs do not identify a person, so no subject ID was inferred.",
            "tilt_bins": "All 13 possible 15-degree tilt bins are emitted; the dataset contains only the values listed in angle_grid_deg.tilt_values_present.",
        },
    }
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description="EXP-010: đánh giá head pose trên Pointing'04 parquet.")
    parser.add_argument("--limit", type=int, default=None, help="Giới hạn số ảnh đầu tiên để chạy thử nhanh.")
    args = parser.parse_args()
    if args.limit is not None and args.limit < 1:
        parser.error("--limit phải lớn hơn 0")
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    summary = _evaluate(args.limit)
    summary_path = OUT_DIR / "summary.json"
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Hoàn tất {summary['n_images_processed']}/{summary['n_images_expected']} ảnh.", flush=True)
    print(f"Mất cả face và pose: {summary['detections']['both_missing_n']} ({summary['detections']['both_missing_rate']}).", flush=True)
    print(f"Dấu tilt suy ra: tilt dương là {summary['tilt_direction_empirical']['positive_tilt_direction']}.", flush=True)
    print(f"Đầu ra: {OUT_DIR}", flush=True)


if __name__ == "__main__":
    main()
