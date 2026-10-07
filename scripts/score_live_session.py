"""Chấm telemetry của một phiên live-session theo các mốc hướng dẫn đã ghi."""

import argparse
import csv
import json
import statistics
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INPUT = ROOT / "docs" / "experiments" / "live_session_2.json"
WARNING_EVENTS = {
    "DROWSINESS_ACUTE",
    "LOOKING_AWAY",
    "LOOKING_DOWN",
    "YAWNING",
    "PHONE_USAGE",
    "DRIVER_ABSENCE",
}
EXPECTED = {
    "eyes_closed": ({"DROWSINESS_ACUTE"}, ("eyes_closed",)),
    "look_left": ({"LOOKING_AWAY"}, ("looking_away",)),
    "look_right": ({"LOOKING_AWAY"}, ("looking_away",)),
    "look_down": ({"LOOKING_DOWN"}, ("looking_down",)),
    "yawn": ({"YAWNING"}, ("yawning",)),
    "phone": ({"PHONE_USAGE"}, ("phone_detected", "phone_usage")),
    "phone_near_face": ({"PHONE_USAGE"}, ("phone_detected", "phone_usage")),
}
CSV_FIELDS = (
    "pha",
    "loai_pha",
    "so_ban_tin",
    "phat_hien_dung",
    "do_tre_s",
    "ti_le_co_pct",
    "thay_mat_pct",
    "bao_gia",
    "tre_chuyen_pha",
    "so_ban_tin_b",
    "phat_hien_dung_b",
    "do_tre_b_s",
    "ti_le_co_b_pct",
    "bao_gia_b",
)


def parse_args():
    parser = argparse.ArgumentParser(description="Chấm điểm tự động telemetry phiên thử DriverGuard.")
    parser.add_argument(
        "--in",
        dest="input_path",
        type=Path,
        default=DEFAULT_INPUT,
        help="Tệp JSON phiên thử (mặc định: docs/experiments/live_session_2.json).",
    )
    parser.add_argument(
        "--csv-out",
        type=Path,
        help="Ghi CSV vào đường dẫn khác; mặc định đặt cạnh JSON với cùng tên .csv.",
    )
    return parser.parse_args()


def as_time(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def frame_events(frame):
    raw_events = frame.get("events") or []
    if isinstance(raw_events, (str, dict)):
        raw_events = [raw_events]
    result = set()
    for event in raw_events:
        if isinstance(event, dict):
            event = event.get("event_type", event.get("type", ""))
        if event:
            result.add(str(event).upper())
    return result


def flag_on(frame, key):
    value = frame.get(key)
    return value is True or value == 1


def percent(numerator, denominator):
    return (100.0 * numerator / denominator) if denominator else None


def score_session(data):
    frames = []
    for frame in data.get("frames", data.get("telemetry", [])) or []:
        stamp = as_time(frame.get("t"))
        if stamp is not None:
            frames.append((stamp, frame))
    frames.sort(key=lambda item: item[0])

    marks = []
    for order, mark in enumerate(data.get("marks", []) or []):
        stamp = as_time(mark.get("t"))
        phase = mark.get("phase")
        if stamp is not None and phase:
            marks.append((stamp, order, str(phase)))
    marks.sort(key=lambda item: (item[0], item[1]))

    rows = []
    occurrences = {}
    for index, (start, _, phase) in enumerate(marks):
        end = marks[index + 1][0] if index + 1 < len(marks) else None
        if phase == "end":
            continue
        phase_frames = [
            frame
            for stamp, frame in frames
            if stamp >= start and (end is None or stamp < end)
        ]
        hold_frames = [
            frame
            for stamp, frame in frames
            if stamp >= start + 2.0 and (end is None or stamp < end)
        ]
        is_expected = phase in EXPECTED
        delayed_count = false_count = 0
        false_count_b = 0
        detected = False if is_expected else None
        detected_b = False if is_expected else None
        latency = None
        latency_b = None
        flag_pct = None
        flag_pct_b = None

        if is_expected:
            expected_events, flag_names = EXPECTED[phase]
            flag_frame_count = sum(any(flag_on(frame, name) for name in flag_names) for frame in phase_frames)
            flag_pct = percent(flag_frame_count, len(phase_frames))
            flag_frame_count_b = sum(any(flag_on(frame, name) for name in flag_names) for frame in hold_frames)
            flag_pct_b = percent(flag_frame_count_b, len(hold_frames))
            signal_times = []
            for frame in phase_frames:
                event_match = bool(frame_events(frame) & expected_events)
                flag_match = any(flag_on(frame, name) for name in flag_names)
                if event_match or flag_match:
                    stamp = as_time(frame.get("t"))
                    if stamp is not None:
                        signal_times.append(stamp)
            signal_times_b = []
            for frame in hold_frames:
                event_match = bool(frame_events(frame) & expected_events)
                flag_match = any(flag_on(frame, name) for name in flag_names)
                if event_match or flag_match:
                    stamp = as_time(frame.get("t"))
                    if stamp is not None:
                        signal_times_b.append(stamp)
            if signal_times:
                detected = True
                latency = max(0.0, min(signal_times) - start)
            if signal_times_b:
                detected_b = True
                latency_b = max(0.0, min(signal_times_b) - (start + 2.0))
            occurrences[phase] = occurrences.get(phase, 0) + 1
            display_phase = f"{phase} ({occurrences[phase]})"
        else:
            display_phase = phase
            for frame in phase_frames:
                event_count = len(frame_events(frame) & WARNING_EVENTS)
                stamp = as_time(frame.get("t"))
                if stamp is None:
                    continue
                if start <= stamp < start + 2.0:
                    delayed_count += event_count
                else:
                    false_count += event_count
                    if stamp >= start + 2.0:
                        false_count_b += event_count

        face_known = any("face_detected" in frame for frame in phase_frames)
        face_pct = percent(sum(flag_on(frame, "face_detected") for frame in phase_frames), len(phase_frames))
        rows.append(
            {
                "pha": display_phase,
                "phase_id": phase,
                "loai_pha": "có cảnh báo" if is_expected else "không báo",
                "so_ban_tin": len(phase_frames),
                "phat_hien_dung": detected,
                "do_tre_s": latency,
                "ti_le_co_pct": flag_pct,
                "thay_mat_pct": face_pct if face_known else None,
                "bao_gia": false_count,
                "tre_chuyen_pha": delayed_count,
                "so_ban_tin_b": len(hold_frames),
                "phat_hien_dung_b": detected_b,
                "do_tre_b_s": latency_b,
                "ti_le_co_b_pct": flag_pct_b,
                "bao_gia_b": false_count_b,
                "is_expected": is_expected,
                "flag_frame_count": sum(
                    any(flag_on(frame, name) for name in EXPECTED[phase][1]) for frame in phase_frames
                ) if is_expected else 0,
                "flag_frame_count_b": sum(
                    any(flag_on(frame, name) for name in EXPECTED[phase][1]) for frame in hold_frames
                ) if is_expected else 0,
                "face_frame_count": sum(flag_on(frame, "face_detected") for frame in phase_frames),
            }
        )

    expected_rows = [row for row in rows if row["is_expected"]]
    detected_count = sum(row["phat_hien_dung"] is True for row in expected_rows)
    false_count = sum(row["bao_gia"] for row in rows)
    delayed_count = sum(row["tre_chuyen_pha"] for row in rows)
    latencies = [row["do_tre_s"] for row in expected_rows if row["do_tre_s"] is not None]
    target_frames = sum(row["so_ban_tin"] for row in expected_rows)
    detected_count_b = sum(row["phat_hien_dung_b"] is True for row in expected_rows)
    false_count_b = sum(row["bao_gia_b"] for row in rows)
    latencies_b = [row["do_tre_b_s"] for row in expected_rows if row["do_tre_b_s"] is not None]
    target_frames_b = sum(row["so_ban_tin_b"] for row in expected_rows)
    summary = {
        "detected": detected_count,
        "expected": len(expected_rows),
        "false_alarms": false_count,
        "transition_delays": delayed_count,
        "median_latency_s": statistics.median(latencies) if latencies else None,
        "flag_pct": percent(sum(row["flag_frame_count"] for row in expected_rows), target_frames),
        "face_pct": percent(sum(row["face_frame_count"] for row in expected_rows), target_frames),
        "window": {
            "detected": detected_count_b,
            "expected": len(expected_rows),
            "false_alarms": false_count_b,
            "median_latency_s": statistics.median(latencies_b) if latencies_b else None,
            "flag_pct": percent(sum(row["flag_frame_count_b"] for row in expected_rows), target_frames_b),
        },
    }
    rows.append(
        {
            "pha": "TỔNG",
            "phase_id": "TỔNG",
            "loai_pha": "tóm tắt",
            "so_ban_tin": target_frames,
            "phat_hien_dung": f"{detected_count}/{len(expected_rows)}",
            "do_tre_s": summary["median_latency_s"],
            "ti_le_co_pct": summary["flag_pct"],
            "thay_mat_pct": summary["face_pct"],
            "bao_gia": false_count,
            "tre_chuyen_pha": delayed_count,
            "so_ban_tin_b": target_frames_b,
            "phat_hien_dung_b": f"{detected_count_b}/{len(expected_rows)}",
            "do_tre_b_s": summary["window"]["median_latency_s"],
            "ti_le_co_b_pct": summary["window"]["flag_pct"],
            "bao_gia_b": false_count_b,
            "is_expected": False,
        }
    )
    return rows, summary


def format_pct(value):
    return "—" if value is None else f"{value:.1f}%"


def format_seconds(value):
    return "—" if value is None else f"{value:.2f}"


def format_rate(numerator, denominator):
    return f"{numerator}/{denominator} ({format_pct(percent(numerator, denominator))})"


def print_report(data, rows, summary, csv_path):
    print("Lưu ý: đây là chấm theo mốc hướng dẫn; người thử có thể phản ứng sớm hoặc muộn.")
    if data.get("label"):
        print(f"Nhãn phiên: {data['label']}")
    if "calibrate_t" not in data:
        print("Mốc hiệu chuẩn: không có trong tệp (phiên cũ).")
    print(f"{'Pha':22} {'Loại':14} {'Tin':>5} {'Đúng':>8} {'Trễ (s)':>9} {'Cờ':>8} {'Thấy mặt':>10} {'Báo giả':>9} {'Trễ pha':>9}")
    print("-" * 105)
    for row in rows:
        detected = row["phat_hien_dung"]
        if detected is True:
            detected_text = "có"
        elif detected is False:
            detected_text = "không"
        else:
            detected_text = str(detected) if detected is not None else "—"
        print(
            f"{row['pha'][:22]:22} {row['loai_pha']:14} {row['so_ban_tin']:5d} {detected_text:>8} "
            f"{format_seconds(row['do_tre_s']):>9} {format_pct(row['ti_le_co_pct']):>8} "
            f"{format_pct(row['thay_mat_pct']):>10} {row['bao_gia']:9d} {row['tre_chuyen_pha']:9d}"
        )
    print(
        "Tổng: phát hiện đúng {detected}/{expected} pha; báo giả {false_alarms}; "
        "trễ chuyển pha {transition_delays}; độ trễ trung vị {median}.".format(
            **summary,
            median=format_seconds(summary["median_latency_s"]),
        )
    )
    window = summary["window"]
    print("Tổng hợp hai cách chấm:")
    print(f"{'Cách chấm':28} {'Phát hiện đúng':>23} {'Báo giả':>10} {'Trễ trung vị (s)':>18}")
    print(
        f"{'(a) theo mốc':28} {format_rate(summary['detected'], summary['expected']):>23} "
        f"{summary['false_alarms']:10d} {format_seconds(summary['median_latency_s']):>18}"
    )
    print(
        f"{'(b) bỏ 2 giây đầu':28} {format_rate(window['detected'], window['expected']):>23} "
        f"{window['false_alarms']:10d} {format_seconds(window['median_latency_s']):>18}"
    )
    print(f"CSV: {csv_path}")


def write_csv(rows, path):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8-sig") as output:
        writer = csv.DictWriter(output, fieldnames=CSV_FIELDS, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            csv_row = {key: row.get(key) for key in CSV_FIELDS}
            for key in ("phat_hien_dung", "phat_hien_dung_b"):
                if isinstance(csv_row[key], bool):
                    csv_row[key] = "có" if csv_row[key] else "không"
            for key in ("do_tre_s", "ti_le_co_pct", "thay_mat_pct", "do_tre_b_s", "ti_le_co_b_pct"):
                value = csv_row[key]
                if value is not None:
                    csv_row[key] = f"{value:.3f}"
            writer.writerow(csv_row)


def main():
    args = parse_args()
    input_path = args.input_path if args.input_path.is_absolute() else ROOT / args.input_path
    input_path = input_path.resolve()
    if not input_path.is_file():
        raise SystemExit(f"Không tìm thấy tệp JSON: {input_path}")
    with input_path.open(encoding="utf-8") as source:
        data = json.load(source)

    csv_path = args.csv_out or input_path.with_suffix(".csv")
    if not csv_path.is_absolute():
        csv_path = ROOT / csv_path
    csv_path = csv_path.resolve()
    rows, summary = score_session(data)
    write_csv(rows, csv_path)
    print_report(data, rows, summary, csv_path)


if __name__ == "__main__":
    main()
