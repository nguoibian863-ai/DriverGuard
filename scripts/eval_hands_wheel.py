"""EXP-011: đo heuristic cổ tay gần/tách khỏi tâm vô lăng trên State Farm.

Chạy từ mọi thư mục: python scripts/eval_hands_wheel.py
YOLO chạy tuần tự ở conf 0.25 và 0.10; không thay đổi pipeline.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import random
import sys
import time
from pathlib import Path
from typing import Any

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ai.perception.pose_tracker import PoseTracker, WEIGHTS  # noqa: E402


CACHE_DIR = ROOT / "data" / "raw" / "state_farm" / "cache"
VIDEO_PATH = ROOT / "data" / "raw" / "web_videos" / "Vuy8SRr1hVA.mp4"
OUTPUT_DIR = ROOT / "docs" / "experiments" / "hands_wheel"
SAMPLE_DIR = ROOT / "data" / "raw" / "state_farm" / "samples"

POSE_CONFS = (0.25, 0.10)
WRIST_CONFS = (0.30, 0.20)
SCALES = ("torso_hip", "shoulder_width", "fallback")
RS = tuple(round(v / 10, 1) for v in range(3, 16))
REPORT_RS = (0.5, 0.8, 1.0, 1.2)
PRIMARY = (0.25, 0.30, "fallback")
SAMPLE_REVIEW_RADIUS = 0.6
CLASS_NAMES = {
    "c0": "lái an toàn",
    "c1": "nhắn tin (phải)",
    "c2": "gọi (phải)",
    "c3": "nhắn tin (trái)",
    "c4": "gọi (trái)",
    "c5": "chỉnh radio",
    "c6": "uống nước",
    "c7": "với ra sau",
    "c8": "trang điểm/tóc",
    "c9": "nói chuyện với hành khách",
}
SCALE_LABELS = {
    "torso_hip": "vai tới hông",
    "shoulder_width": "rộng vai",
    "fallback": "vai tới hông, thiếu hông thì rộng vai",
}
SKELETON = ((5, 7), (7, 9), (6, 8), (8, 10), (5, 6), (5, 11), (6, 12), (11, 12))


def _conf_key(value: float) -> str:
    return f"{value:.2f}"


def _r_key(value: float) -> str:
    return f"r_{value:.1f}".replace(".", "_")


def _config_key(pose_conf: float, wrist_conf: float, scale: str) -> str:
    return f"pose{_conf_key(pose_conf)}_wrist{_conf_key(wrist_conf)}_{scale}"


def _safe_float(value: float | None) -> float | None:
    if value is None or not math.isfinite(value):
        return None
    return float(value)


def _visible(point: np.ndarray | None, threshold: float = 0.30) -> bool:
    return point is not None and len(point) >= 3 and float(point[2]) >= threshold


def _pose_prediction(model: Any, frame: np.ndarray, pose_conf: float, device: Any, imgsz: int) -> np.ndarray | None:
    """Chọn người có bbox lớn nhất như PoseTracker, giữ cả raw keypoint khi vai/mũi thiếu."""
    results = model.predict(
        frame,
        conf=pose_conf,
        device=device,
        verbose=False,
        imgsz=imgsz,
    )
    best: tuple[float, np.ndarray] | None = None
    for result in results:
        if result.boxes is None or result.keypoints is None:
            continue
        boxes = result.boxes.xyxy.cpu().numpy()
        points = result.keypoints.data.cpu().numpy()
        for index in range(min(len(boxes), len(points))):
            x1, y1, x2, y2 = boxes[index]
            area = max(0.0, float(x2 - x1)) * max(0.0, float(y2 - y1))
            if best is None or area > best[0]:
                best = area, points[index]
    if best is None or len(best[1]) < 17:
        return None
    return np.asarray(best[1][:17], dtype=np.float32)


def _geometry(points: np.ndarray | None) -> dict[str, Any]:
    empty = {
        "shoulder_mid": None,
        "torso_hip_scale": None,
        "shoulder_width_scale": None,
        "scales": {name: None for name in SCALES},
        "scale_reasons": {name: "pose_missing" for name in SCALES},
    }
    if points is None or len(points) < 17:
        return empty

    left_shoulder, right_shoulder = points[5], points[6]
    left_hip, right_hip = points[11], points[12]
    shoulders_ok = _visible(left_shoulder) and _visible(right_shoulder)
    hips_ok = _visible(left_hip) and _visible(right_hip)
    if not shoulders_ok:
        reason = "shoulder_missing"
        return {**empty, "scale_reasons": {name: reason for name in SCALES}}

    shoulder_mid = (left_shoulder[:2] + right_shoulder[:2]) / 2.0
    shoulder_width = float(np.linalg.norm(left_shoulder[:2] - right_shoulder[:2]))
    torso_scale = None
    if hips_ok:
        hip_mid = (left_hip[:2] + right_hip[:2]) / 2.0
        torso_scale = float(np.linalg.norm(shoulder_mid - hip_mid))

    scales: dict[str, float | None] = {
        "torso_hip": torso_scale if torso_scale and torso_scale > 1e-6 else None,
        "shoulder_width": shoulder_width if shoulder_width > 1e-6 else None,
        "fallback": None,
    }
    scales["fallback"] = scales["torso_hip"] or scales["shoulder_width"]
    reasons = {
        "torso_hip": "ok" if scales["torso_hip"] is not None else ("hip_missing" if not hips_ok else "zero_scale"),
        "shoulder_width": "ok" if scales["shoulder_width"] is not None else "zero_scale",
        "fallback": "torso_hip" if scales["torso_hip"] is not None else ("shoulder_width" if scales["shoulder_width"] is not None else "zero_scale"),
    }
    return {
        "shoulder_mid": shoulder_mid,
        "torso_hip_scale": scales["torso_hip"],
        "shoulder_width_scale": scales["shoulder_width"],
        "scales": scales,
        "scale_reasons": reasons,
    }


def _normalized_wrists(
    points: np.ndarray | None,
    geometry: dict[str, Any],
    wrist_conf: float,
    scale_name: str,
) -> tuple[list[tuple[float, float] | None], list[float | None]]:
    positions: list[tuple[float, float] | None] = [None, None]
    confidences: list[float | None] = [None, None]
    if points is None or len(points) < 17:
        return positions, confidences
    for out_index, kp_index in enumerate((9, 10)):
        point = points[kp_index]
        confidences[out_index] = float(point[2])
        if not _visible(point, wrist_conf):
            continue
        scale = geometry["scales"].get(scale_name)
        origin = geometry["shoulder_mid"]
        if scale is None or origin is None:
            continue
        normalized = (point[:2] - origin) / float(scale)
        positions[out_index] = (float(normalized[0]), float(normalized[1]))
    return positions, confidences


def _median_center(positions: list[tuple[float, float]]) -> tuple[float, float] | None:
    if not positions:
        return None
    values = np.asarray(positions, dtype=np.float64)
    return float(np.median(values[:, 0])), float(np.median(values[:, 1]))


def _distances(
    positions: list[tuple[float, float] | None], center: tuple[float, float] | None
) -> list[float | None]:
    if center is None:
        return [None, None]
    return [
        None if pos is None else float(math.hypot(pos[0] - center[0], pos[1] - center[1]))
        for pos in positions
    ]


def _statuses(distances: list[float | None], radius: float) -> list[str]:
    return ["unknown" if distance is None else ("away" if distance > radius else "on") for distance in distances]


def _state(statuses: list[str]) -> str:
    if "unknown" in statuses:
        return "unknown"
    count = statuses.count("away")
    return ("none", "one", "two")[count]


def _class_of(path: Path) -> str:
    return path.parent.name


def _split_c0(files: list[Path]) -> tuple[set[Path], set[Path]]:
    c0_files = sorted(path for path in files if _class_of(path) == "c0")
    shuffled = list(c0_files)
    random.Random(0).shuffle(shuffled)
    cut = len(shuffled) // 2
    return set(shuffled[:cut]), set(shuffled[cut:])


def _auc(labels: list[int], scores: list[float]) -> float | None:
    positives = sum(labels)
    negatives = len(labels) - positives
    if positives == 0 or negatives == 0:
        return None
    ordered = sorted(zip(scores, labels), key=lambda pair: pair[0])
    rank_sum = 0.0
    start = 0
    while start < len(ordered):
        end = start + 1
        while end < len(ordered) and ordered[end][0] == ordered[start][0]:
            end += 1
        average_rank = ((start + 1) + end) / 2.0
        rank_sum += average_rank * sum(label for _, label in ordered[start:end])
        start = end
    return (rank_sum - positives * (positives + 1) / 2.0) / (positives * negatives)


def _binary_at_radius(
    observations: list[dict[str, Any]], radius: float, observed_only_auc: bool = True
) -> dict[str, Any]:
    labels: list[int] = []
    scores: list[float] = []
    auc_labels: list[int] = []
    auc_scores: list[float] = []
    tp = fp = fn = tn = 0
    observed = 0
    for item in observations:
        label = int(item["class"] in {f"c{i}" for i in range(1, 9)})
        score_max_distance = item["score_max_distance"]
        score = float(score_max_distance) if score_max_distance is not None else 0.0
        prediction = score > radius
        labels.append(label)
        scores.append(score)
        if item["usable_wrist_count"] > 0:
            auc_labels.append(label)
            auc_scores.append(score)
            observed += 1
        if label and prediction:
            tp += 1
        elif label:
            fn += 1
        elif prediction:
            fp += 1
        else:
            tn += 1
    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    return {
        "radius": radius,
        "precision": precision,
        "recall": recall,
        "f1": f1,
        "fpr": fp / (fp + tn) if fp + tn else None,
        "auc_all_unknown_as_no_away": _auc(labels, scores),
        "auc_observed_only": _auc(auc_labels, auc_scores) if observed_only_auc else None,
        "coverage_at_least_one_usable_wrist": observed / len(observations) if observations else 0.0,
        "tp": tp,
        "fp": fp,
        "fn": fn,
        "tn": tn,
    }


def _base_record(path: Path, points_by_conf: dict[float, np.ndarray | None], calibration: set[Path], test: set[Path]) -> dict[str, Any]:
    cls = _class_of(path)
    split = "c0_calibration" if path in calibration else ("c0_test" if path in test else "all_other")
    return {"path": path, "class": cls, "split": split, "poses": points_by_conf}


def _make_rows(
    base_records: list[dict[str, Any]], centers: dict[str, dict[str, Any]]
) -> tuple[list[dict[str, Any]], dict[tuple[str, float, float, str], dict[str, Any]]]:
    rows: list[dict[str, Any]] = []
    lookup: dict[tuple[str, float, float, str], dict[str, Any]] = {}
    for record in base_records:
        path: Path = record["path"]
        cls: str = record["class"]
        for pose_conf in POSE_CONFS:
            points = record["poses"].get(pose_conf)
            geometry = _geometry(points)
            for wrist_conf in WRIST_CONFS:
                for scale_name in SCALES:
                    config = _config_key(pose_conf, wrist_conf, scale_name)
                    center_item = centers[config]
                    center = center_item["center"]
                    positions, wrist_confidences = _normalized_wrists(points, geometry, wrist_conf, scale_name)
                    distances = _distances(positions, center)
                    known_count = sum(distance is not None for distance in distances)
                    visible_count = sum(conf is not None and conf >= wrist_conf for conf in wrist_confidences)
                    score_max = max((value for value in distances if value is not None), default=None)
                    row: dict[str, Any] = {
                        "image": path.relative_to(ROOT).as_posix(),
                        "class": cls,
                        "class_name": CLASS_NAMES.get(cls, ""),
                        "split": record["split"],
                        "evaluation_population": record["split"] != "c0_calibration",
                        "pose_conf": pose_conf,
                        "wrist_conf": wrist_conf,
                        "normalization": scale_name,
                        "normalization_label": SCALE_LABELS[scale_name],
                        "normalization_valid": geometry["scales"].get(scale_name) is not None,
                        "normalization_reason": geometry["scale_reasons"].get(scale_name),
                        "shoulder_mid_x": _safe_float(None if geometry["shoulder_mid"] is None else geometry["shoulder_mid"][0]),
                        "shoulder_mid_y": _safe_float(None if geometry["shoulder_mid"] is None else geometry["shoulder_mid"][1]),
                        "torso_hip_scale_px": geometry["torso_hip_scale"],
                        "shoulder_width_scale_px": geometry["shoulder_width_scale"],
                        "center_x": None if center is None else center[0],
                        "center_y": None if center is None else center[1],
                        "center_calibration_wrist_observations": center_item["n_wrist_observations"],
                        "center_calibration_images_with_wrist": center_item["n_images_with_wrist"],
                        "left_wrist_x": None if points is None else float(points[9][0]),
                        "left_wrist_y": None if points is None else float(points[9][1]),
                        "left_wrist_conf": wrist_confidences[0],
                        "left_wrist_norm_x": None if positions[0] is None else positions[0][0],
                        "left_wrist_norm_y": None if positions[0] is None else positions[0][1],
                        "left_wrist_distance": distances[0],
                        "right_wrist_x": None if points is None else float(points[10][0]),
                        "right_wrist_y": None if points is None else float(points[10][1]),
                        "right_wrist_conf": wrist_confidences[1],
                        "right_wrist_norm_x": None if positions[1] is None else positions[1][0],
                        "right_wrist_norm_y": None if positions[1] is None else positions[1][1],
                        "right_wrist_distance": distances[1],
                        "wrist_visible_count": visible_count,
                        "wrist_unknown_count": 2 - visible_count,
                        "usable_wrist_count": known_count,
                        "score_max_distance": score_max,
                        "any_wrist_away_at_any_radius": None,
                    }
                    for radius in RS:
                        statuses = _statuses(distances, radius)
                        known_away = statuses.count("away")
                        key = _r_key(radius)
                        row[f"left_status_{key}"] = statuses[0]
                        row[f"right_status_{key}"] = statuses[1]
                        row[f"away_hands_known_{key}"] = known_away
                        row[f"image_state_{key}"] = _state(statuses)
                        row[f"at_least_one_away_{key}"] = known_away >= 1
                        row[f"both_away_{key}"] = statuses == ["away", "away"]
                        row[f"unknown_image_{key}"] = "unknown" in statuses
                    rows.append(row)
                    lookup[(path.as_posix(), pose_conf, wrist_conf, scale_name)] = row
    return rows, lookup


def _class_summary(rows: list[dict[str, Any]]) -> dict[str, Any]:
    n = len(rows)
    if n == 0:
        return {"n_images": 0}
    return {
        "n_images": n,
        "wrist_visible_rate_left_right_average": sum(row["wrist_visible_count"] for row in rows) / (2 * n),
        "both_wrists_visible_rate": sum(row["wrist_visible_count"] == 2 for row in rows) / n,
        "at_least_one_wrist_visible_rate": sum(row["wrist_visible_count"] >= 1 for row in rows) / n,
        "unknown_wrist_image_rate": sum(row["wrist_unknown_count"] > 0 for row in rows) / n,
        "normalization_missing_rate": sum(not row["normalization_valid"] for row in rows) / n,
        "usable_at_least_one_wrist_rate": sum(row["usable_wrist_count"] >= 1 for row in rows) / n,
        "rates_by_radius": {
            _r_key(radius): {
                "radius": radius,
                "at_least_one_away_rate": sum(bool(row[f"at_least_one_away_{_r_key(radius)}"]) for row in rows) / n,
                "both_away_rate": sum(bool(row[f"both_away_{_r_key(radius)}"]) for row in rows) / n,
                "unknown_image_rate": sum(bool(row[f"unknown_image_{_r_key(radius)}"]) for row in rows) / n,
                "state_rate": {
                    state: sum(row[f"image_state_{_r_key(radius)}"] == state for row in rows) / n
                    for state in ("none", "one", "two", "unknown")
                },
            }
            for radius in REPORT_RS
        },
    }


def _format_csv_value(value: Any) -> Any:
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False)
    if isinstance(value, (np.floating, np.integer)):
        return value.item()
    return value


def _write_per_image(path: Path, rows: list[dict[str, Any]]) -> None:
    base_fields = [
        "image", "class", "class_name", "split", "evaluation_population", "pose_conf", "wrist_conf",
        "normalization", "normalization_label", "normalization_valid", "normalization_reason",
        "shoulder_mid_x", "shoulder_mid_y", "torso_hip_scale_px", "shoulder_width_scale_px",
        "center_x", "center_y", "center_calibration_wrist_observations", "center_calibration_images_with_wrist",
        "left_wrist_x", "left_wrist_y", "left_wrist_conf", "left_wrist_norm_x", "left_wrist_norm_y", "left_wrist_distance",
        "right_wrist_x", "right_wrist_y", "right_wrist_conf", "right_wrist_norm_x", "right_wrist_norm_y", "right_wrist_distance",
        "wrist_visible_count", "wrist_unknown_count", "usable_wrist_count", "score_max_distance",
    ]
    threshold_fields = []
    for radius in RS:
        key = _r_key(radius)
        threshold_fields.extend(
            [
                f"left_status_{key}", f"right_status_{key}", f"away_hands_known_{key}",
                f"image_state_{key}", f"at_least_one_away_{key}", f"both_away_{key}", f"unknown_image_{key}",
            ]
        )
    fields = base_fields + threshold_fields
    with path.open("w", newline="", encoding="utf-8-sig") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow({key: _format_csv_value(value) for key, value in row.items()})


def _draw_sample(path: Path, points: np.ndarray | None, row: dict[str, Any], category: str, radius: float) -> None:
    image = cv2.imread(str(path))
    if image is None:
        return
    if points is not None:
        for start, end in SKELETON:
            if _visible(points[start], 0.20) and _visible(points[end], 0.20):
                cv2.line(image, tuple(np.round(points[start][:2]).astype(int)), tuple(np.round(points[end][:2]).astype(int)), (180, 180, 180), 2)
        statuses = _statuses(
            [row["left_wrist_distance"], row["right_wrist_distance"]], radius
        )
        for index, kp_index in enumerate((9, 10)):
            if not _visible(points[kp_index], 0.20):
                continue
            color = {"away": (0, 0, 255), "on": (0, 210, 0), "unknown": (0, 165, 255)}[statuses[index]]
            xy = tuple(np.round(points[kp_index][:2]).astype(int))
            cv2.circle(image, xy, 8, color, -1)
            cv2.putText(image, ("L" if index == 0 else "R") + ":" + statuses[index], (xy[0] + 8, xy[1] - 4), cv2.FONT_HERSHEY_SIMPLEX, 0.45, color, 1, cv2.LINE_AA)
    lines = [
        f"{category} | {row['class']} | R={radius:.1f} | {row['image_state_' + _r_key(radius)]}",
        f"pose={row['pose_conf']:.2f} wrist={row['wrist_conf']:.2f} | norm={row['normalization']}",
    ]
    for index, line in enumerate(lines):
        text_size, baseline = cv2.getTextSize(line, cv2.FONT_HERSHEY_SIMPLEX, 0.54, 1)
        y = 26 + 22 * index
        cv2.rectangle(image, (8, y - text_size[1] - 3), (16 + text_size[0], y + baseline + 2), (0, 0, 0), -1)
        cv2.putText(image, line, (12, y), cv2.FONT_HERSHEY_SIMPLEX, 0.54, (255, 255, 255), 1, cv2.LINE_AA)
    destination = SAMPLE_DIR / f"{category}_{path.parent.name}_{path.stem}.jpg"
    cv2.imwrite(str(destination), image, [int(cv2.IMWRITE_JPEG_QUALITY), 90])


def _save_samples(
    base_records: list[dict[str, Any]],
    lookup: dict[tuple[str, float, float, str], dict[str, Any]],
    radius: float = SAMPLE_REVIEW_RADIUS,
) -> dict[str, Any]:
    config = PRIMARY
    candidates = [record for record in base_records if record["split"] != "c0_calibration"]
    rng = random.Random(0)
    chosen: list[tuple[dict[str, Any], str]] = []
    selected: set[Path] = set()

    def take(group: list[dict[str, Any]], count: int, label: str) -> None:
        eligible = [record for record in group if record["path"] not in selected]
        rng.shuffle(eligible)
        for record in eligible[:count]:
            selected.add(record["path"])
            chosen.append((record, label))

    c0_away = [
        record for record in candidates
        if record["class"] == "c0"
        and lookup[(record["path"].as_posix(), *config)][f"at_least_one_away_{_r_key(radius)}"]
    ]
    c78_on = [
        record for record in candidates
        if record["class"] in {"c7", "c8"}
        and not lookup[(record["path"].as_posix(), *config)][f"at_least_one_away_{_r_key(radius)}"]
        and not lookup[(record["path"].as_posix(), *config)][f"unknown_image_{_r_key(radius)}"]
    ]
    unknown = [
        record for record in candidates
        if lookup[(record["path"].as_posix(), *config)][f"unknown_image_{_r_key(radius)}"]
    ]
    take(c0_away, 10, "c0_away")
    take(c78_on, 10, "c7c8_no_away")
    take(unknown, 10, "unknown")
    take(candidates, 10, "random")
    SAMPLE_DIR.mkdir(parents=True, exist_ok=True)
    for record, label in chosen:
        row = lookup[(record["path"].as_posix(), *config)]
        _draw_sample(record["path"], record["poses"].get(config[0]), row, label, radius)
    return {
        "directory": SAMPLE_DIR.relative_to(ROOT).as_posix(),
        "max_images": 40,
        "saved_unique_images": len(chosen),
        "primary_radius": radius,
        "primary_configuration": _config_key(*config),
        "counts_by_requested_category": {
            label: sum(category == label for _, category in chosen)
            for label in ("c0_away", "c7c8_no_away", "unknown", "random")
        },
        "files": [f"{label}_{record['path'].parent.name}_{record['path'].stem}.jpg" for record, label in chosen],
    }


def _video_geometry_summary(
    video_records: list[dict[str, Any]],
    c0_centers: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    result: dict[str, Any] = {"available": bool(video_records)}
    for pose_conf in POSE_CONFS:
        for wrist_conf in WRIST_CONFS:
            for scale_name in SCALES:
                config = _config_key(pose_conf, wrist_conf, scale_name)
                normalized_per_frame: list[list[tuple[float, float] | None]] = []
                all_wrist_positions: list[tuple[float, float]] = []
                for record in video_records:
                    geometry = record["geometry"][pose_conf]
                    positions, _ = _normalized_wrists(record["poses"].get(pose_conf), geometry, wrist_conf, scale_name)
                    normalized_per_frame.append(positions)
                    all_wrist_positions.extend(position for position in positions if position is not None)
                own_center = _median_center(all_wrist_positions)
                centers = {
                    "video_median": own_center,
                    "c0_calibration": c0_centers[config]["center"],
                }
                center_results: dict[str, Any] = {}
                for center_name, center in centers.items():
                    by_radius: dict[str, Any] = {}
                    for radius in RS:
                        counts = {"none": 0, "one": 0, "two": 0, "unknown": 0}
                        for positions in normalized_per_frame:
                            state = _state(_statuses(_distances(positions, center), radius))
                            counts[state] += 1
                        total = len(video_records)
                        by_radius[_r_key(radius)] = {
                            "radius": radius,
                            "frames": counts,
                            "rates": {key: value / total if total else 0.0 for key, value in counts.items()},
                        }
                    center_results[center_name] = {
                        "available": center is not None,
                        "center_x": None if center is None else center[0],
                        "center_y": None if center is None else center[1],
                        "wrist_observations_for_center": len(all_wrist_positions) if center_name == "video_median" else c0_centers[config]["n_wrist_observations"],
                        "rates_by_radius": by_radius,
                    }
                result[config] = {
                    "pose_conf": pose_conf,
                    "wrist_conf": wrist_conf,
                    "normalization": scale_name,
                    "video_median_center": center_results["video_median"],
                    "c0_calibration_center": center_results["c0_calibration"],
                }
    return result


def _run(force: bool) -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    summary_path = OUTPUT_DIR / "summary.json"
    csv_path = OUTPUT_DIR / "per_image.csv"
    sample_existing = list(SAMPLE_DIR.glob("*.jpg")) if SAMPLE_DIR.exists() else []
    existing_outputs = [path for path in (summary_path, csv_path) if path.exists()]
    if (existing_outputs or sample_existing) and not force:
        raise FileExistsError(
            "Đầu ra đã tồn tại; không ghi đè. Xem nội dung rồi chạy lại với --force nếu muốn thay thế."
        )

    image_files = sorted(CACHE_DIR.glob("c[0-9]/*.jpg")) if CACHE_DIR.exists() else []
    calibration, c0_test = _split_c0(image_files)
    dataset_counts = {f"c{i}": sum(_class_of(path) == f"c{i}" for path in image_files) for i in range(10)}
    tracker: PoseTracker | None = None
    base_records: list[dict[str, Any]] = []
    centers: dict[str, dict[str, Any]] = {}
    rows: list[dict[str, Any]] = []
    metrics: dict[str, Any] = {}
    sample_result: dict[str, Any] | None = None
    video_records: list[dict[str, Any]] = []
    video_meta: dict[str, Any] = {"available": False, "path": VIDEO_PATH.relative_to(ROOT).as_posix()}
    t0 = time.time()

    if image_files or VIDEO_PATH.exists():
        tracker = PoseTracker()
        print(f"PoseTracker weights={WEIGHTS} device={tracker.device} imgsz={tracker.imgsz}", flush=True)

    if image_files:
        print(f"State Farm: {len(image_files)} ảnh; bắt đầu suy luận tuần tự.", flush=True)
        for index, path in enumerate(image_files, start=1):
            image = cv2.imread(str(path))
            poses: dict[float, np.ndarray | None] = {}
            if image is not None:
                for pose_conf in POSE_CONFS:
                    poses[pose_conf] = _pose_prediction(tracker.model, image, pose_conf, tracker.device, tracker.imgsz)
            else:
                poses = {pose_conf: None for pose_conf in POSE_CONFS}
            base_records.append(_base_record(path, poses, calibration, c0_test))
            if index % 100 == 0 or index == len(image_files):
                print(f"State Farm {index}/{len(image_files)}", flush=True)

        for pose_conf in POSE_CONFS:
            for wrist_conf in WRIST_CONFS:
                for scale_name in SCALES:
                    config = _config_key(pose_conf, wrist_conf, scale_name)
                    positions: list[tuple[float, float]] = []
                    images_with_wrist: set[Path] = set()
                    for record in base_records:
                        if record["split"] != "c0_calibration":
                            continue
                        points = record["poses"].get(pose_conf)
                        geometry = _geometry(points)
                        wrists, _ = _normalized_wrists(points, geometry, wrist_conf, scale_name)
                        present = [position for position in wrists if position is not None]
                        if present:
                            images_with_wrist.add(record["path"])
                            positions.extend(present)
                    center = _median_center(positions)
                    centers[config] = {
                        "center": center,
                        "n_wrist_observations": len(positions),
                        "n_images_with_wrist": len(images_with_wrist),
                        "calibration_images": len(calibration),
                        "calibration_seed": 0,
                    }
        rows, lookup = _make_rows(base_records, centers)
        for pose_conf in POSE_CONFS:
            for wrist_conf in WRIST_CONFS:
                for scale_name in SCALES:
                    config = _config_key(pose_conf, wrist_conf, scale_name)
                    in_population = [
                        row for row in rows
                        if row["evaluation_population"]
                        and row["pose_conf"] == pose_conf
                        and row["wrist_conf"] == wrist_conf
                        and row["normalization"] == scale_name
                    ]
                    per_class: dict[str, Any] = {}
                    for cls in [f"c{i}" for i in range(10)]:
                        cls_rows = [row for row in in_population if row["class"] == cls]
                        if cls == "c0" or cls == "c9" or cls in {f"c{i}" for i in range(1, 9)}:
                            per_class[cls] = _class_summary(cls_rows)
                    binary = []
                    positive_classes = {f"c{i}" for i in range(1, 9)}
                    for row in in_population:
                        is_c0_test_negative = row["class"] == "c0" and row["split"] == "c0_test"
                        if is_c0_test_negative or row["class"] in positive_classes:
                            binary.append(row)
                    binary_results = {
                        _r_key(radius): _binary_at_radius(binary, radius)
                        for radius in RS
                    }
                    metrics[config] = {
                        "pose_conf": pose_conf,
                        "wrist_conf": wrist_conf,
                        "normalization": scale_name,
                        "normalization_label": SCALE_LABELS[scale_name],
                        "center_from_c0_calibration": centers[config],
                        "per_class": per_class,
                        "relative_binary_label_metrics": {
                            "positive_classes": [f"c{i}" for i in range(1, 9)],
                            "negative_class": "c0_test",
                            "label_caveat": "Nhãn gần đúng: c1-c8 thường có ít nhất một tay rời; c0 là lái an toàn. Không có nhãn trực tiếp tay trên/rời vô lăng; không dùng để kết luận cả hai tay rời.",
                            "threshold_scan": binary_results,
                        },
                    }
        sample_result = _save_samples(base_records, lookup)
    else:
        metrics = {}
        centers = {
            _config_key(pose_conf, wrist_conf, scale_name): {
                "center": None,
                "n_wrist_observations": 0,
                "n_images_with_wrist": 0,
                "calibration_images": 0,
                "calibration_seed": 0,
            }
            for pose_conf in POSE_CONFS
            for wrist_conf in WRIST_CONFS
            for scale_name in SCALES
        }

    if VIDEO_PATH.exists():
        capture = cv2.VideoCapture(str(VIDEO_PATH))
        fps = float(capture.get(cv2.CAP_PROP_FPS))
        reported_frames = int(capture.get(cv2.CAP_PROP_FRAME_COUNT))
        frame_index = 0
        print(f"Video sanity: {VIDEO_PATH.name}, {reported_frames} khung báo cáo, fps={fps:.3f}.", flush=True)
        while True:
            ok, frame = capture.read()
            if not ok:
                break
            poses: dict[float, np.ndarray | None] = {}
            if tracker is None:
                tracker = PoseTracker()
            for pose_conf in POSE_CONFS:
                poses[pose_conf] = _pose_prediction(tracker.model, frame, pose_conf, tracker.device, tracker.imgsz)
            geometries = {pose_conf: _geometry(points) for pose_conf, points in poses.items()}
            video_records.append({"frame": frame_index, "poses": poses, "geometry": geometries})
            frame_index += 1
            if frame_index % 100 == 0:
                print(f"Video {frame_index} khung", flush=True)
        capture.release()
        video_meta = {
            "available": True,
            "path": VIDEO_PATH.relative_to(ROOT).as_posix(),
            "reported_frames": reported_frames,
            "processed_frames": len(video_records),
            "fps": fps,
            "duration_seconds_from_metadata": reported_frames / fps if fps > 0 else None,
            "duration_seconds_processed": len(video_records) / fps if fps > 0 else None,
            "notes": "Tâm video lấy trung vị cổ tay chuẩn hóa trên toàn clip (mô tả, không phải ground truth); so sánh với tâm c0 từ nửa hiệu chuẩn nếu cache tải được.",
        }
        video_meta["configurations"] = _video_geometry_summary(video_records, centers)
    elif image_files:
        video_meta["notes"] = "Không tìm thấy tệp video sanity."

    _write_per_image(csv_path, rows)
    summary = {
        "experiment": "EXP-011",
        "created_at_local": time.strftime("%Y-%m-%d %H:%M:%S"),
        "dataset": {
            "available": bool(image_files),
            "cache_directory": CACHE_DIR.relative_to(ROOT).as_posix(),
            "n_images": len(image_files),
            "counts_by_class": dataset_counts,
            "expected_images": 1500,
            "expected_per_class": 150,
            "sample_seed": 0,
            "c0_split": {
                "method": "random.Random(0).shuffle(sorted(c0 image paths); first floor(n/2) for calibration, remainder held out",
                "calibration_images": len(calibration),
                "test_images": len(c0_test),
                "possible_person_leakage": "Không có ID người; ảnh cùng người có thể rơi vào hai nửa.",
            },
            "download_note": "" if image_files else "Không có cache ảnh; fetch_state_farm_sample.py bị chặn bởi HTTPS proxy 127.0.0.1:9 nên không thể đo State Farm trong lần chạy này.",
            "classes": CLASS_NAMES,
        },
        "pose": {
            "weights": str(WEIGHTS.relative_to(ROOT).as_posix()) if WEIGHTS.is_relative_to(ROOT) else str(WEIGHTS),
            "pose_confidences": list(POSE_CONFS),
            "wrist_keypoints": {"left": 9, "right": 10, "confidence_thresholds": list(WRIST_CONFS)},
            "normalization_keypoints": {"shoulders": [5, 6], "hips": [11, 12], "normalization_joint_confidence": 0.30},
            "normalizations": SCALE_LABELS,
            "radii": list(RS),
            "report_radii": list(REPORT_RS),
            "center_definition": "Trung vị X/Y của các cổ tay chuẩn hóa gộp trên c0 calibration split; riêng video_median là trung vị trên chính clip.",
            "pose_selection": "BBox có diện tích lớn nhất, cùng cách chọn người của PoseTracker; raw keypoint giữ lại kể cả khi PoseTracker.detect sẽ trả None vì thiếu đặc trưng vai/mũi.",
        },
        "dataset_metrics": metrics,
        "sample_review_images": sample_result or {"available": False, "directory": SAMPLE_DIR.relative_to(ROOT).as_posix(), "saved_unique_images": 0},
        "video_sanity": video_meta,
        "limitations": [
            "State Farm không có nhãn tay trên/rời vô lăng; lớp hành vi chỉ là nhãn gần đúng.",
            "Tâm c0 được học từ một nửa c0 và chấm trên nửa còn lại; không có ID người để tránh rò rỉ cùng người.",
            "Góc camera bên hông làm co chiếu vai và có thể làm sai chuẩn hóa rộng vai; vai tới hông cũng có thể thiếu/foreshorten.",
            "Cổ tay không đủ confidence hoặc không chuẩn hóa được được giữ là unknown, không tính là away.",
            "Không có lớp bảo đảm hai tay rời; tỷ lệ hai tay rời chỉ là mô tả theo heuristic.",
        ],
        "runtime_seconds": time.time() - t0,
        "outputs": {"summary": summary_path.relative_to(ROOT).as_posix(), "per_image": csv_path.relative_to(ROOT).as_posix()},
    }
    with summary_path.open("w", encoding="utf-8") as stream:
        json.dump(summary, stream, ensure_ascii=False, indent=2, allow_nan=False)
        stream.write("\n")
    print(f"Đã ghi {summary_path.relative_to(ROOT)} và {csv_path.relative_to(ROOT)}", flush=True)
    print(f"State Farm={len(image_files)} ảnh; video={len(video_records)} khung; runtime={time.time() - t0:.1f}s", flush=True)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--force", action="store_true", help="Cho phép thay thế summary/per_image/samples hiện có sau khi đã kiểm tra.")
    args = parser.parse_args()
    _run(force=args.force)


if __name__ == "__main__":
    main()
