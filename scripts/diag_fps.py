"""Chẩn đoán nút thắt FPS: đo riêng từng khâu của vòng lặp camera trong `ai/runtime/worker.py`.

Thí nghiệm 15 cho thấy pipeline khuôn mặt chạy ~92 FPS trên CPU, nên FPS camera trung vị 15
(mục UR-15 cần >= 20) phải đến từ khâu khác. Script này tách bốn mức để biết khâu nào chậm:

  A. chỉ đọc khung hình            -> trần FPS của chính camera
  B. A + nhận diện khuôn mặt       -> chi phí MediaPipe
  C. B + vẽ lớp phủ và mã hoá JPEG -> chi phí dựng ảnh xem trực tiếp
  D. C + YOLO điện thoại và pose   -> ảnh hưởng của hai luồng YOLO (GIL và GPU)

Chạy trên máy có camera:   python scripts/diag_fps.py --camera 0 --seconds 15
Chạy thử trên video có sẵn: python scripts/diag_fps.py --video <đường dẫn> --seconds 15
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import cv2

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ai.runtime.pipeline import DriverPipeline, PhoneObservation
from ai.runtime.thresholds import load_thresholds
from ai.runtime.worker import _draw_overlay, _encode

STAGES = ("A_doc_khung", "B_them_khuon_mat", "C_them_lop_phu_jpeg", "D_them_yolo")


def open_source(args: argparse.Namespace) -> cv2.VideoCapture:
    if args.video:
        return cv2.VideoCapture(args.video)
    # CAP_DSHOW chỉ có trên Windows; trên nền khác dùng mặc định như worker
    backend = cv2.CAP_DSHOW if hasattr(cv2, "CAP_DSHOW") and sys.platform == "win32" else 0
    capture = cv2.VideoCapture(args.camera, backend) if backend else cv2.VideoCapture(args.camera)
    capture.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    capture.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
    return capture


def measure(stage: str, args: argparse.Namespace) -> dict:
    capture = open_source(args)
    if not capture.isOpened():
        return {"stage": stage, "error": "khong_mo_duoc_nguon"}

    tracker = phone_thread = pose_thread = None
    pipeline = DriverPipeline(load_thresholds())
    try:
        if stage != "A_doc_khung":
            from ai.perception.face_landmarks import FaceLandmarkTracker

            tracker = FaceLandmarkTracker()
        if stage == "D_them_yolo":
            from ai.runtime.worker import _PhoneThread, _PoseThread

            phone_thread, pose_thread = _PhoneThread(), _PoseThread()
            phone_thread.start()
            pose_thread.start()

        costs: dict[str, float] = {"read": 0.0, "face": 0.0, "render": 0.0}
        frames = 0
        deadline = time.perf_counter() + args.seconds
        started = time.perf_counter()
        while time.perf_counter() < deadline:
            mark = time.perf_counter()
            ok, frame = capture.read()
            if not ok:
                if args.video:  # hết video thì quay lại đầu để đo đủ thời gian
                    capture.set(cv2.CAP_PROP_POS_FRAMES, 0)
                    continue
                break
            costs["read"] += time.perf_counter() - mark
            frames += 1
            now = time.time()

            telemetry = {}
            if tracker is not None:
                mark = time.perf_counter()
                observation, _face_box, _ = tracker.process(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB), now)
                telemetry, _ = pipeline.update(now, observation, PhoneObservation())
                costs["face"] += time.perf_counter() - mark
            if stage in ("C_them_lop_phu_jpeg", "D_them_yolo"):
                mark = time.perf_counter()
                telemetry.setdefault("fps", {})
                telemetry.setdefault("latency_ms", {})
                if phone_thread is not None:
                    phone_thread.frame = frame
                    if pose_thread.ident is not None:
                        pose_thread.frame = frame
                _encode(_draw_overlay(frame, telemetry, None, []))
                costs["render"] += time.perf_counter() - mark
        elapsed = time.perf_counter() - started
    finally:
        capture.release()
        if tracker is not None:
            tracker.close()
        for thread in (phone_thread, pose_thread):
            if thread is not None:
                thread.running = False

    if not frames:
        return {"stage": stage, "error": "khong_doc_duoc_khung_nao"}
    return {
        "stage": stage,
        "fps": round(frames / elapsed, 1),
        "frames": frames,
        "ms_per_frame": {k: round(v / frames * 1000, 2) for k, v in costs.items()},
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--camera", type=int, default=0)
    parser.add_argument("--video", default="", help="dùng video thay camera (để thử không cần thiết bị)")
    parser.add_argument("--seconds", type=float, default=15.0, help="thời gian đo mỗi mức")
    parser.add_argument("--stages", default=",".join(STAGES))
    parser.add_argument("--out", type=Path, default=ROOT / "docs" / "experiments" / "fps_diag.json")
    args = parser.parse_args()

    results = [measure(stage, args) for stage in args.stages.split(",") if stage in STAGES]
    summary = {
        "source": args.video or f"camera {args.camera}",
        "seconds_per_stage": args.seconds,
        "stages": results,
        "ghi_chu": "A là trần FPS của camera. Nếu A đã thấp (~15) thì nút thắt là camera/phơi sáng, "
                   "không phải xử lý. Nếu A cao mà D thấp thì nút thắt là hai luồng YOLO.",
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(summary, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
