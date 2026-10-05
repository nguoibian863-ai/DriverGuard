from ai.runtime.pipeline import DriverPipeline, FaceObservation, PhoneObservation
from ai.runtime.thresholds import Thresholds


def face(ear=0.30, mar=0.20, yaw=0.0, pitch=0.0):
    return FaceObservation(ear=ear, mar=mar, yaw=yaw, pitch=pitch, roll=0.0)


def run(pipe, start, seconds, make_face, make_phone=None, hz=10):
    out = []
    n = int(seconds * hz)
    for i in range(n + 1):
        t = start + i / hz
        tele, ev = pipe.update(t, make_face(t), make_phone(t) if make_phone else None)
        out.append((t, tele, ev))
    return out


def calibrated_pipe():
    pipe = DriverPipeline(Thresholds())
    run(pipe, 0.0, 5.0, lambda t: face(yaw=10.0, pitch=-5.0))  # camera lệch trục
    return pipe


def test_normal_driving_stays_normal():
    pipe = calibrated_pipe()
    res = run(pipe, 5.1, 10.0, lambda t: face(yaw=10.0, pitch=-5.0))
    assert res[-1][1]["calibrated"] is True
    assert res[-1][1]["risk_level"] == "NORMAL"
    assert not any(ev for _, _, ev in res)


def test_eyes_closed_triggers_acute_danger():
    pipe = calibrated_pipe()
    res = run(pipe, 5.1, 3.0, lambda t: face(ear=0.10, yaw=10.0, pitch=-5.0))
    events = [e for _, _, ev in res for e in ev]
    assert [e["event_type"] for e in events] == ["DROWSINESS_ACUTE"]
    assert res[-1][1]["eyes_closed"] is True
    assert res[-1][1]["risk_level"] == "DANGER"


def test_short_blink_does_not_trigger():
    pipe = calibrated_pipe()
    res = run(pipe, 5.1, 1.0, lambda t: face(ear=0.10, yaw=10.0, pitch=-5.0))
    assert not any(ev for _, _, ev in res)
    assert res[-1][1]["eyes_closed"] is False


def test_looking_away_relative_to_calibration():
    pipe = calibrated_pipe()
    res = run(pipe, 5.1, 3.0, lambda t: face(yaw=10.0 + 45.0, pitch=-5.0))
    types = [e["event_type"] for _, _, ev in res for e in ev]
    assert "LOOKING_AWAY" in types
    assert res[-1][1]["relative_yaw"] == 45.0


def test_phone_usage_event():
    pipe = calibrated_pipe()
    res = run(
        pipe, 5.1, 3.0, lambda t: face(yaw=10.0, pitch=-5.0),
        lambda t: PhoneObservation(detected=True, usage_candidate=True),
    )
    types = [e["event_type"] for _, _, ev in res for e in ev]
    assert "PHONE_USAGE" in types
    assert res[-1][1]["phone_usage"] is True


def test_driver_absence():
    pipe = calibrated_pipe()
    res = run(pipe, 5.1, 4.0, lambda t: None)
    types = [e["event_type"] for _, _, ev in res for e in ev]
    assert "DRIVER_ABSENCE" in types
    assert res[-1][1]["face_detected"] is False


def test_risk_decays_after_danger():
    pipe = calibrated_pipe()
    run(pipe, 5.1, 3.0, lambda t: face(ear=0.10, yaw=10.0, pitch=-5.0))
    res = run(pipe, 8.2, 10.0, lambda t: face(yaw=10.0, pitch=-5.0))
    scores = [tele["risk_score"] for _, tele, _ in res]
    assert scores[0] > scores[-1]
    assert scores[-1] < 40


def test_mute_flag():
    pipe = calibrated_pipe()
    pipe.mute(6.0, 15)
    tele, _ = pipe.update(7.0, face(yaw=10.0, pitch=-5.0))
    assert tele["muted"] is True
    tele, _ = pipe.update(22.0, face(yaw=10.0, pitch=-5.0))
    assert tele["muted"] is False


def test_recalibrate():
    pipe = calibrated_pipe()
    pipe.start_calibration()
    tele, _ = pipe.update(6.0, face())
    assert tele["calibrated"] is False


def test_ear_threshold_personalised_to_small_eyes():
    # Tài xế mắt nhỏ: EAR mở mắt ~0.21. Ngưỡng cố định 0.20 sẽ báo giả.
    pipe = DriverPipeline(Thresholds())
    run(pipe, 0.0, 5.0, lambda t: face(ear=0.21))
    assert abs(pipe.ear_threshold - 0.147) < 0.01
    res = run(pipe, 5.1, 6.0, lambda t: face(ear=0.20))
    assert not any(ev for _, _, ev in res)
    res = run(pipe, 11.2, 3.0, lambda t: face(ear=0.08))
    assert [e["event_type"] for _, _, ev in res for e in ev] == ["DROWSINESS_ACUTE"]
