from ai.perception.pose_tracker import PoseObservation, compute_pose_features
from ai.runtime.pipeline import DriverPipeline, FaceObservation
from ai.runtime.thresholds import Thresholds


def keypoints(nose=(50.0, 50.0), left_shoulder_conf=0.9):
    points = [(0.0, 0.0, 0.0) for _ in range(17)]
    points[0] = (nose[0], nose[1], 0.95)  # nose
    points[3] = (35.0, 55.0, 0.8)  # left ear
    points[4] = (65.0, 55.0, 0.6)  # right ear
    points[5] = (0.0, 100.0, left_shoulder_conf)  # left shoulder
    points[6] = (100.0, 100.0, 0.9)  # right shoulder
    return tuple(points)


def observation(nose=(50.0, 50.0), observed_at=None):
    points = keypoints(nose)
    features = compute_pose_features(points)
    assert features is not None
    return PoseObservation(points, *features, observed_at=observed_at)


def calibrated_pipeline(use_pose_fallback=True):
    thresholds = Thresholds(
        use_pose_fallback=use_pose_fallback,
        calibration_s=1.0,
        head_s=2.0,
        absence_s=3.0,
    )
    pipeline = DriverPipeline(thresholds)
    face = FaceObservation(ear=0.30, mar=0.20, yaw=0.0, pitch=0.0, roll=0.0)
    neutral = observation()
    for index in range(12):
        pipeline.update(index / 10, face, pose=neutral)
    assert pipeline.calibrator.is_calibrated
    assert pipeline.pose_yaw_baseline == 0.0
    assert pipeline.pose_pitch_baseline == -0.5
    return pipeline


def collect(pipeline, start, seconds, pose, hz=10):
    events = []
    telemetries = []
    for index in range(int(seconds * hz) + 1):
        now = start + index / hz
        tele, current_events = pipeline.update(now, None, pose=pose)
        telemetries.append(tele)
        events.extend(event["event_type"] for event in current_events)
    return telemetries, events


def test_pose_features_for_forward_left_right_and_down():
    forward = compute_pose_features(keypoints())
    left = compute_pose_features(keypoints(nose=(25.0, 50.0)))
    right = compute_pose_features(keypoints(nose=(75.0, 50.0)))
    down = compute_pose_features(keypoints(nose=(50.0, 90.0)))

    assert forward == (0.0, -0.5, 0.20000000000000007)
    assert left is not None and left[0] == -0.25
    assert right is not None and right[0] == 0.25
    assert down is not None and down[1] == -0.1


def test_pose_features_reject_missing_shoulder_confidence():
    assert compute_pose_features(keypoints(left_shoulder_conf=0.29)) is None


def test_pose_disabled_keeps_face_loss_behavior_and_pose_telemetry():
    pipeline = calibrated_pipeline(use_pose_fallback=False)
    down = observation(nose=(50.0, 90.0))
    telemetries, events = collect(pipeline, 1.2, 3.2, down)

    assert "LOOKING_DOWN" not in events
    assert "DRIVER_ABSENCE" in events
    assert telemetries[-1]["pose"]["person"] is True
    assert telemetries[-1]["pose"]["pitch_rel"] == 0.4


def test_fresh_pose_without_baseline_preserves_held_away_after_face_loss():
    for use_pose_fallback in (False, True):
        pipeline = DriverPipeline(
            Thresholds(
                use_pose_fallback=use_pose_fallback,
                calibration_s=1.0,
                head_s=2.0,
                absence_s=3.0,
            )
        )
        neutral_face = FaceObservation(ear=0.30, mar=0.20, yaw=0.0, pitch=0.0, roll=0.0)
        for index in range(11):
            pipeline.update(index / 10, neutral_face)

        assert pipeline.calibrator.is_calibrated
        assert pipeline.pose_yaw_baseline is None
        assert pipeline.pose_pitch_baseline is None

        turned_face = FaceObservation(ear=0.30, mar=0.20, yaw=35.0, pitch=0.0, roll=0.0)
        pipeline.update(1.1, turned_face)
        assert pipeline.last_rel_yaw == 35.0

        telemetries, events = collect(pipeline, 1.2, 2.1, observation())
        assert "LOOKING_AWAY" in events
        assert "DRIVER_ABSENCE" not in events
        assert telemetries[-1]["pose"]["yaw_rel"] is None


def test_pose_fallback_triggers_looking_down_after_head_duration():
    pipeline = calibrated_pipeline()
    _, events = collect(pipeline, 1.2, 2.2, observation(nose=(50.0, 90.0)))
    assert "LOOKING_DOWN" in events


def test_pose_fallback_triggers_looking_away_for_either_yaw_direction():
    for x in (10.0, 90.0):
        pipeline = calibrated_pipeline()
        _, events = collect(pipeline, 1.2, 2.2, observation(nose=(x, 50.0)))
        assert "LOOKING_AWAY" in events


def test_fresh_pose_prevents_driver_absence_without_face():
    pipeline = calibrated_pipeline()
    _, events = collect(pipeline, 1.2, 4.0, observation())
    assert "DRIVER_ABSENCE" not in events


def test_pose_older_than_max_age_is_ignored():
    pipeline = calibrated_pipeline()
    stale = observation(nose=(50.0, 90.0), observed_at=0.0)
    telemetries, events = collect(pipeline, 1.2, 3.2, stale)

    assert "LOOKING_DOWN" not in events
    assert "DRIVER_ABSENCE" in events
    assert telemetries[-1]["pose"]["pitch_rel"] == 0.4
