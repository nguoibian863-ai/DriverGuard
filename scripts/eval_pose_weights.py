"""So sánh weights/preprocessing YOLO pose trên video web (EXP-009)."""

from __future__ import annotations

import csv
import gc
import json
import math
import statistics
import sys
import time
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import cv2
import numpy as np

for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, "reconfigure"):
        _stream.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ai.perception.face_landmarks import FaceLandmarkTracker
from ai.perception.pose_tracker import compute_pose_features

VIDEO_DIR = ROOT / "data" / "raw" / "web_videos"
OUT_DIR = ROOT / "docs" / "experiments" / "web_video"
JSON_PATH = OUT_DIR / "pose_weights.json"
CSV_PATH = OUT_DIR / "pose_weights.csv"
VIDEO_IDS = ("FD5ctXyExqc", "VPnBwC1fOJY", "lKIkpzwuaWs")
WEIGHTS = (
    "yolo26m-pose.pt",
    "yolo26l-pose.pt",
    "yolo26x-pose.pt",
    "yolo11m-pose.pt",
    "yolo11x-pose.pt",
)
PREPROCESSING = ("none", "clahe_gray", "gamma_0.6")
CONFIDENCES = (0.25, 0.10)
IMGSZ = 640
FRAME_STRIDE = 2  # 30 cấu hình trên FD: giảm một nửa số lượt suy luận, ghi rõ trong kết quả.
CLAHE = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
GAMMA_06_LUT = np.array([round(((i / 255.0) ** 0.6) * 255.0) for i in range(256)], dtype=np.uint8)


def config_key(weights: str, preprocessing: str, conf: float) -> str:
    return f"{weights}|{preprocessing}|conf={conf:.2f}"


def preprocess(frame: np.ndarray, method: str) -> np.ndarray:
    if method == "none":
        return frame
    if method == "clahe_gray":
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        enhanced = CLAHE.apply(gray)
        return cv2.cvtColor(enhanced, cv2.COLOR_GRAY2BGR)
    if method == "gamma_0.6":
        return cv2.LUT(frame, GAMMA_06_LUT)
    raise ValueError(f"Tiền xử lý không biết: {method}")


def _expected_video_info(video_id: str) -> dict[str, Any]:
    path = VIDEO_DIR / f"{video_id}.mp4"
    if not path.is_file():
        raise FileNotFoundError(f"Không tìm thấy video đã có: {path}")
    cap = cv2.VideoCapture(str(path))
    try:
        if not cap.isOpened():
            raise RuntimeError(f"Không mở được video: {path}")
        fps = float(cap.get(cv2.CAP_PROP_FPS))
        frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    finally:
        cap.release()
    if not math.isfinite(fps) or fps <= 0 or frame_count <= 0:
        raise RuntimeError(f"Metadata video không hợp lệ: {video_id}, {frame_count=}, {fps=}")
    return {
        "video_id": video_id,
        "source": path.relative_to(ROOT).as_posix(),
        "frame_count": frame_count,
        "fps": fps,
        "duration_s": frame_count / fps,
    }


def _valid_bits(bits: Any, frame_count: int) -> bool:
    return isinstance(bits, str) and len(bits) == frame_count and set(bits) <= {"0", "1"}


def _read_face_cache_from_pose_json(video_id: str, frame_count: int) -> dict[str, Any] | None:
    if not JSON_PATH.is_file():
        return None
    try:
        payload = json.loads(JSON_PATH.read_text(encoding="utf-8"))
        cache = payload.get("videos", {}).get(video_id, {}).get("face_missing_cache", {})
        if cache.get("frame_count") == frame_count and _valid_bits(cache.get("bits"), frame_count):
            return cache
    except (OSError, ValueError, TypeError):
        return None
    return None


def _read_face_cache_from_exp008_csv(video_id: str, frame_count: int) -> dict[str, Any] | None:
    """EXP-008 đã chạy FaceLandmarkTracker từng khung; tái dùng CSV đầy đủ đó."""
    path = OUT_DIR / f"{video_id}.csv"
    if not path.is_file():
        return None
    bits: list[str] = []
    try:
        with path.open("r", newline="", encoding="utf-8-sig") as handle:
            reader = csv.DictReader(handle)
            if not reader.fieldnames or not {"frame_index", "face_detected"} <= set(reader.fieldnames):
                return None
            for expected_index, row in enumerate(reader):
                if int(row["frame_index"]) != expected_index:
                    return None
                value = row["face_detected"].strip().lower()
                if value not in {"true", "false", "1", "0"}:
                    return None
                bits.append("0" if value in {"true", "1"} else "1")
    except (OSError, ValueError, TypeError, KeyError):
        return None
    if len(bits) != frame_count:
        return None
    return {
        "frame_count": frame_count,
        "bits": "".join(bits),
        "encoding": "1=mất mặt MediaPipe, 0=có mặt",
        "source": path.relative_to(ROOT).as_posix(),
    }


def _measure_face_missing(video_id: str, info: dict[str, Any]) -> dict[str, Any]:
    path = VIDEO_DIR / f"{video_id}.mp4"
    tracker = FaceLandmarkTracker()
    bits: list[str] = []
    cap = cv2.VideoCapture(str(path))
    try:
        if not cap.isOpened():
            raise RuntimeError(f"Không mở được video để chạy MediaPipe: {path}")
        index = 0
        while True:
            ok, frame = cap.read()
            if not ok:
                break
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            face, _box, _landmarks = tracker.process(rgb, index / info["fps"])
            bits.append("0" if face is not None else "1")
            index += 1
            if index % 500 == 0:
                print(f"[{video_id}] MediaPipe {index}/{info['frame_count']} khung", flush=True)
    finally:
        cap.release()
        tracker.close()
    if len(bits) != info["frame_count"]:
        raise RuntimeError(
            f"Số khung MediaPipe đọc được ({len(bits)}) khác metadata ({info['frame_count']}) cho {video_id}"
        )
    return {
        "frame_count": len(bits),
        "bits": "".join(bits),
        "encoding": "1=mất mặt MediaPipe, 0=có mặt",
        "source": "FaceLandmarkTracker; chạy một lần toàn bộ clip",
    }


def get_face_missing_cache(video_id: str, info: dict[str, Any]) -> dict[str, Any]:
    cache = _read_face_cache_from_pose_json(video_id, info["frame_count"])
    if cache is not None:
        print(f"[{video_id}] Dùng cache MediaPipe trong pose_weights.json", flush=True)
        return cache
    cache = _read_face_cache_from_exp008_csv(video_id, info["frame_count"])
    if cache is not None:
        print(f"[{video_id}] Dùng cache MediaPipe từ EXP-008: {cache['source']}", flush=True)
        return cache
    print(f"[{video_id}] Không có cache hợp lệ; chạy FaceLandmarkTracker một lần", flush=True)
    return _measure_face_missing(video_id, info)


def _write_checkpoint(payload: dict[str, Any]) -> None:
    JSON_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _new_payload(device: str) -> dict[str, Any]:
    return {
        "experiment": "EXP-009",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "device": device,
        "imgsz": IMGSZ,
        "frame_stride": FRAME_STRIDE,
        "frame_sampling": "Chạy YOLO trên frame_index % 2 == 0; cache mất mặt MediaPipe cho mọi khung.",
        "preprocessing": {
            "none": "khung BGR gốc",
            "clahe_gray": "BGR->gray; CLAHE clipLimit=3.0, tileGridSize=(8,8); gray->BGR 3 kênh",
            "gamma_0.6": "lookup table round((i/255)^0.6*255) trên các kênh BGR",
        },
        "feature_definition": (
            "Khung có feature khi compute_pose_features trên keypoints của bbox người lớn nhất trả khác None; "
            "giữ nguyên ngưỡng conf keypoint 0.3 và yêu cầu mũi + hai vai của hàm."
        ),
        "latency_definition": "Trung vị ms/frame gồm biến đổi ảnh, YOLO predict và lấy kết quả/keypoints về CPU; không gồm giải mã video.",
        "vram_definition": "torch.cuda.max_memory_allocated MiB, reset trước mỗi cấu hình; gồm model đã nạp.",
        "videos": {},
        "weights": {},
        "results": [],
        "best_fd_configs": [],
        "secondary_configs": [],
        "notes": [],
    }


def _config_shell(weights: str, preprocessing: str, conf: float, video_id: str) -> dict[str, Any]:
    return {
        "video_id": video_id,
        "weights": weights,
        "preprocessing": preprocessing,
        "conf": conf,
        "imgsz": IMGSZ,
        "frame_stride": FRAME_STRIDE,
        "status": "pending",
        "frames_evaluated": None,
        "person_frames": None,
        "person_rate": None,
        "feature_frames": None,
        "feature_rate": None,
        "face_missing_frames_evaluated": None,
        "person_frames_face_missing": None,
        "person_rate_face_missing": None,
        "feature_frames_face_missing": None,
        "feature_rate_face_missing": None,
        "median_latency_ms": None,
        "peak_memory_allocated_mib": None,
        "error": None,
    }


def _ratio(numerator: int, denominator: int) -> float | None:
    return round(numerator / denominator, 6) if denominator else None


def _extract_counts(result: Any, threshold: float) -> tuple[bool, bool]:
    """Trả có bbox người và compute_pose_features hợp lệ trên bbox lớn nhất."""
    boxes = getattr(result, "boxes", None)
    keypoints = getattr(result, "keypoints", None)
    if boxes is None or len(boxes) == 0:
        return False, False
    if keypoints is None or keypoints.data is None:
        return True, False
    xyxy = boxes.xyxy.detach().cpu().numpy()
    confs = boxes.conf.detach().cpu().numpy()
    points = keypoints.data.detach().cpu().numpy()
    eligible = [i for i in range(min(len(xyxy), len(confs), len(points))) if float(confs[i]) >= threshold]
    if not eligible:
        return True, False
    # Threshold đã được truyền vào predict; filter lặp lại để phép đo vẫn đúng nếu backend bỏ qua conf.
    areas = [max(0.0, float(xyxy[i][2] - xyxy[i][0])) * max(0.0, float(xyxy[i][3] - xyxy[i][1])) for i in eligible]
    largest = eligible[int(np.argmax(areas))]
    features = compute_pose_features(points[largest])
    return True, features is not None


def _is_oom(exc: BaseException, torch: Any) -> bool:
    oom_type = getattr(torch.cuda, "OutOfMemoryError", ()) if torch is not None else ()
    if oom_type and isinstance(exc, oom_type):
        return True
    message = str(exc).lower()
    return "out of memory" in message or "cuda error: memory allocation" in message


def _fill_status_rows(
    payload: dict[str, Any], weights: str, video_ids: list[str], status: str, error: str | None
) -> None:
    for video_id in video_ids:
        for preprocessing in PREPROCESSING:
            for conf in CONFIDENCES:
                row = _config_shell(weights, preprocessing, conf, video_id)
                row["status"] = status
                row["error"] = error
                payload["results"].append(row)


def _load_model(weights: str, torch: Any) -> Any:
    from ultralytics import YOLO
    from ultralytics.utils.downloads import attempt_download_asset

    models_dir = ROOT / "models"
    models_dir.mkdir(parents=True, exist_ok=True)
    weight_path = models_dir / weights
    if not weight_path.exists():
        attempt_download_asset(str(weight_path))
    if not weight_path.is_file():
        raise FileNotFoundError(f"Không tải được weights vào {weight_path}")
    return YOLO(str(weight_path))


def evaluate_video_for_model(
    model: Any,
    torch: Any,
    device: str,
    weights: str,
    video_id: str,
    info: dict[str, Any],
    face_cache: dict[str, Any],
    configs: list[tuple[str, float]],
) -> list[dict[str, Any]]:
    path = VIDEO_DIR / f"{video_id}.mp4"
    bits = face_cache["bits"]
    output_rows: list[dict[str, Any]] = []
    for preprocessing, conf in configs:
        row = _config_shell(weights, preprocessing, conf, video_id)
        counts = defaultdict(int)
        latencies: list[float] = []
        peak_bytes = 0
        cap = cv2.VideoCapture(str(path))
        if not cap.isOpened():
            raise RuntimeError(f"Không mở được video: {path}")
        try:
            frame_index = 0
            while True:
                ok, frame = cap.read()
                if not ok:
                    break
                if frame_index % FRAME_STRIDE == 0:
                    face_missing = bits[frame_index] == "1"
                    if device.startswith("cuda"):
                        torch.cuda.synchronize()
                        torch.cuda.reset_peak_memory_stats(0)
                    started = time.perf_counter()
                    prepared = preprocess(frame, preprocessing)
                    predictions = model.predict(
                        prepared,
                        conf=conf,
                        device=0 if device.startswith("cuda") else "cpu",
                        verbose=False,
                        imgsz=IMGSZ,
                    )
                    person, feature = _extract_counts(predictions[0], conf)
                    if device.startswith("cuda"):
                        torch.cuda.synchronize()
                        peak_bytes = max(peak_bytes, int(torch.cuda.max_memory_allocated(0)))
                    latencies.append((time.perf_counter() - started) * 1000.0)
                    counts["frames"] += 1
                    counts["person"] += int(person)
                    counts["feature"] += int(feature)
                    if face_missing:
                        counts["face_missing"] += 1
                        counts["person_face_missing"] += int(person)
                        counts["feature_face_missing"] += int(feature)
                    del predictions, prepared
                frame_index += 1
                if frame_index % 1000 == 0:
                    print(
                        f"[{video_id}][{weights}][{preprocessing}][{conf:.2f}] "
                        f"{frame_index}/{info['frame_count']} khung đã đọc",
                        flush=True,
                    )
        finally:
            cap.release()
        if frame_index != info["frame_count"]:
            raise RuntimeError(f"Đọc {frame_index}/{info['frame_count']} khung ở {video_id}")
        row.update(
            {
                "status": "ok",
                "frames_evaluated": counts["frames"],
                "person_frames": counts["person"],
                "person_rate": _ratio(counts["person"], counts["frames"]),
                "feature_frames": counts["feature"],
                "feature_rate": _ratio(counts["feature"], counts["frames"]),
                "face_missing_frames_evaluated": counts["face_missing"],
                "person_frames_face_missing": counts["person_face_missing"],
                "person_rate_face_missing": _ratio(counts["person_face_missing"], counts["face_missing"]),
                "feature_frames_face_missing": counts["feature_face_missing"],
                "feature_rate_face_missing": _ratio(counts["feature_face_missing"], counts["face_missing"]),
                "median_latency_ms": round(statistics.median(latencies), 3) if latencies else None,
                "peak_memory_allocated_mib": round(peak_bytes / (1024 * 1024), 2) if device.startswith("cuda") else None,
            }
        )
        output_rows.append(row)
    return output_rows


def _model_cleanup(model: Any, torch: Any) -> None:
    if model is not None:
        del model
    gc.collect()
    if torch is not None and torch.cuda.is_available():
        try:
            torch.cuda.synchronize()
        except Exception:
            pass
        torch.cuda.empty_cache()
        gc.collect()


def _rank_fd_configs(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    usable = [
        row for row in rows
        if row["video_id"] == "FD5ctXyExqc" and row["status"] == "ok"
    ]
    usable.sort(
        key=lambda row: (
            row["feature_rate_face_missing"] if row["feature_rate_face_missing"] is not None else -1,
            row["person_rate_face_missing"] if row["person_rate_face_missing"] is not None else -1,
            row["feature_rate"] if row["feature_rate"] is not None else -1,
            -(row["median_latency_ms"] if row["median_latency_ms"] is not None else float("inf")),
        ),
        reverse=True,
    )
    return usable[:2]


def _write_csv(rows: list[dict[str, Any]]) -> None:
    fields = [
        "video_id", "weights", "preprocessing", "conf", "imgsz", "frame_stride", "status",
        "frames_evaluated", "person_frames", "person_rate", "feature_frames", "feature_rate",
        "face_missing_frames_evaluated", "person_frames_face_missing", "person_rate_face_missing",
        "feature_frames_face_missing", "feature_rate_face_missing", "median_latency_ms",
        "peak_memory_allocated_mib", "error",
    ]
    with CSV_PATH.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows({field: row.get(field) for field in fields} for row in rows)


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    import torch

    device = "cuda:0" if torch.cuda.is_available() else "cpu"
    payload = _new_payload(device)
    for video_id in VIDEO_IDS:
        info = _expected_video_info(video_id)
        cache = get_face_missing_cache(video_id, info)
        info["face_missing_cache"] = cache
        info["face_missing_frames_total"] = cache["bits"].count("1")
        payload["videos"][video_id] = info
    _write_checkpoint(payload)

    total_lost_eval = {
        video_id: sum(
            1 for i in range(info["frame_count"])
            if i % FRAME_STRIDE == 0 and info["face_missing_cache"]["bits"][i] == "1"
        )
        for video_id, info in payload["videos"].items()
    }
    payload["notes"].append(
        "MediaPipe mất mặt được cache cho mọi khung, tái dùng từ pose_weights.json hoặc CSV EXP-008; "
        "YOLO chạy mỗi 2 khung do 30 tổ hợp dự kiến trên FD."
    )
    payload["notes"].append(
        "Xếp hạng trên FD theo feature rate trong các khung mất mặt, rồi person rate trong các khung mất mặt, "
        "feature rate toàn clip, cuối cùng ưu tiên latency thấp."
    )
    _write_checkpoint(payload)

    model_status: dict[str, dict[str, Any]] = {}
    fd_configs = [(prep, conf) for prep in PREPROCESSING for conf in CONFIDENCES]
    for weights in WEIGHTS:
        print(f"\n=== FD5ctXyExqc: nạp {weights} trên {device} ===", flush=True)
        model = None
        stage = "load"
        try:
            model = _load_model(weights, torch)
            stage = "eval"
            fd_rows = evaluate_video_for_model(
                model, torch, device, weights, "FD5ctXyExqc", payload["videos"]["FD5ctXyExqc"],
                payload["videos"]["FD5ctXyExqc"]["face_missing_cache"], fd_configs,
            )
            payload["results"].extend(fd_rows)
            model_status[weights] = {"status": "ok", "error": None}
            payload["weights"][weights] = model_status[weights]
            print(f"[{weights}] hoàn tất FD: {len(fd_rows)} cấu hình", flush=True)
        except Exception as exc:
            oom = _is_oom(exc, torch)
            status = "OOM" if oom else "unavailable" if stage == "load" else "error"
            message = f"{type(exc).__name__}: {exc}"[:1000]
            # Nếu một cấu hình không chạy xong, đánh dấu cả weight chưa có bộ kết quả FD so sánh đầy đủ.
            payload["results"] = [r for r in payload["results"] if r["weights"] != weights]
            _fill_status_rows(payload, weights, ["FD5ctXyExqc"], status, message)
            model_status[weights] = {"status": status, "error": message}
            payload["weights"][weights] = model_status[weights]
            print(f"[{weights}] {status}: {message}", flush=True)
            if oom:
                try:
                    torch.cuda.empty_cache()
                except Exception:
                    pass
        finally:
            _model_cleanup(model, torch)
            model = None
            _write_checkpoint(payload)

    best = _rank_fd_configs(payload["results"])
    baseline_key = config_key("yolo26m-pose.pt", "none", 0.25)
    secondary_keys = {config_key(r["weights"], r["preprocessing"], r["conf"]) for r in best}
    secondary_keys.add(baseline_key)
    secondary_configs: list[tuple[str, str, float]] = []
    for key in secondary_keys:
        weight, preprocessing, conf_text = key.split("|")
        secondary_configs.append((weight, preprocessing, float(conf_text.removeprefix("conf="))))
    secondary_configs.sort(key=lambda item: (WEIGHTS.index(item[0]), PREPROCESSING.index(item[1]), item[2]))
    payload["best_fd_configs"] = [
        {"rank": index, "config": config_key(r["weights"], r["preprocessing"], r["conf"]),
         "feature_rate_face_missing": r["feature_rate_face_missing"],
         "person_rate_face_missing": r["person_rate_face_missing"],
         "feature_rate": r["feature_rate"], "median_latency_ms": r["median_latency_ms"]}
        for index, r in enumerate(best, start=1)
    ]
    payload["secondary_configs"] = [config_key(*item) for item in secondary_configs]
    _write_checkpoint(payload)
    print(f"\nCấu hình FD xếp hạng đầu: {payload['best_fd_configs']}", flush=True)

    for weights in dict.fromkeys(item[0] for item in secondary_configs):
        if model_status.get(weights, {}).get("status") != "ok":
            for video_id in VIDEO_IDS[1:]:
                matching = [(prep, conf) for w, prep, conf in secondary_configs if w == weights]
                for preprocessing, conf in matching:
                    row = _config_shell(weights, preprocessing, conf, video_id)
                    row["status"] = model_status.get(weights, {}).get("status", "unavailable")
                    row["error"] = model_status.get(weights, {}).get("error")
                    payload["results"].append(row)
            continue
        model = None
        stage = "load"
        try:
            print(f"\n=== Video kiểm tra chéo: nạp {weights} ===", flush=True)
            model = _load_model(weights, torch)
            stage = "eval"
            configs_for_weight = [(prep, conf) for w, prep, conf in secondary_configs if w == weights]
            for video_id in VIDEO_IDS[1:]:
                rows = evaluate_video_for_model(
                    model, torch, device, weights, video_id, payload["videos"][video_id],
                    payload["videos"][video_id]["face_missing_cache"], configs_for_weight,
                )
                payload["results"].extend(rows)
                _write_checkpoint(payload)
                print(f"[{video_id}][{weights}] hoàn tất {len(rows)} cấu hình", flush=True)
        except Exception as exc:
            oom = _is_oom(exc, torch)
            status = "OOM" if oom else "unavailable" if stage == "load" else "error"
            message = f"{type(exc).__name__}: {exc}"[:1000]
            payload["results"] = [
                row for row in payload["results"]
                if not (row["weights"] == weights and row["video_id"] in VIDEO_IDS[1:])
            ]
            for video_id in VIDEO_IDS[1:]:
                for preprocessing, conf in [(prep, conf) for w, prep, conf in secondary_configs if w == weights]:
                    row = _config_shell(weights, preprocessing, conf, video_id)
                    row["status"] = status
                    row["error"] = message
                    payload["results"].append(row)
            payload["notes"].append(f"Kiểm tra chéo {weights}: {status} ({message})")
            print(f"[{weights}] kiểm tra chéo {status}: {message}", flush=True)
        finally:
            _model_cleanup(model, torch)
            _write_checkpoint(payload)

    for video_id, info in payload["videos"].items():
        info["face_missing_frames_evaluated_at_stride"] = total_lost_eval[video_id]
    _write_csv(payload["results"])
    _write_checkpoint(payload)
    print(f"\nĐã ghi {JSON_PATH}", flush=True)
    print(f"Đã ghi {CSV_PATH}", flush=True)
    print("video | weight | prep | conf | person | feature | feature khi mất mặt | ms/frame | VRAM MiB | status")
    for row in payload["results"]:
        if row["video_id"] != "FD5ctXyExqc":
            continue
        print(
            f"{row['video_id']} | {row['weights']} | {row['preprocessing']} | {row['conf']:.2f} | "
            f"{row['person_rate']} | {row['feature_rate']} | {row['feature_rate_face_missing']} | "
            f"{row['median_latency_ms']} | {row['peak_memory_allocated_mib']} | {row['status']}"
        )


if __name__ == "__main__":
    main()
