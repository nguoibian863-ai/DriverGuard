import os
import sqlite3

from fastapi.testclient import TestClient

os.environ["DRIVERGUARD_START_WORKER"] = "0"
from app.main import app


def _telemetry(**kw):
    base = {"timestamp": "2026-10-05T08:00:00+00:00", "face_detected": True, "events": []}
    base.update(kw)
    return base


def test_config_returns_thresholds(tmp_path, monkeypatch):
    monkeypatch.setenv("DRIVERGUARD_DB", str(tmp_path / "t.db"))
    with TestClient(app) as client:
        cfg = client.get("/api/v1/config").json()
        assert cfg["thresholds"]["eyes_closed_s"] == 1.8
        assert "ear_threshold" in cfg["thresholds"]


def test_camera_connected_even_without_face(tmp_path, monkeypatch):
    # camera_connected không được phụ thuộc vào việc thấy mặt
    monkeypatch.setenv("DRIVERGUARD_DB", str(tmp_path / "t.db"))
    with TestClient(app) as client:
        app.state.bridge.process_telemetry(_telemetry(face_detected=False))
        assert client.get("/api/v1/health").json()["camera_connected"] is True
        app.state.bridge.process_telemetry(_telemetry(error="camera_unavailable"))
        assert client.get("/api/v1/health").json()["camera_connected"] is False


def test_events_from_telemetry_are_saved_with_session(tmp_path, monkeypatch):
    db = tmp_path / "t.db"
    monkeypatch.setenv("DRIVERGUARD_DB", str(db))
    with TestClient(app) as client:
        event = {
            "event_type": "DROWSINESS_ACUTE", "started_at": "2026-10-05T08:00:00+00:00",
            "duration_ms": 1800, "risk_score": 90.0, "risk_level": "DANGER",
            "confidence": 0.9, "reason": "test",
        }
        app.state.bridge.process_telemetry(_telemetry(events=[event]))
        assert client.get("/api/v1/events").json()["events"][0]["event_type"] == "DROWSINESS_ACUTE"
        session_id = app.state.session["id"]
    row = sqlite3.connect(db).execute(
        "select event_count, status from sessions where id=?", (session_id,)
    ).fetchone()
    assert row == (1, "COMPLETED")


def test_mute_rejects_invalid_duration(tmp_path, monkeypatch):
    monkeypatch.setenv("DRIVERGUARD_DB", str(tmp_path / "t.db"))
    with TestClient(app) as client:
        assert client.post("/api/v1/alerts/mute", json={"duration_seconds": 0}).status_code == 422
