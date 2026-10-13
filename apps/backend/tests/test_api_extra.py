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


def test_sessions_list_detail_and_stop(tmp_path, monkeypatch):
    monkeypatch.setenv("DRIVERGUARD_DB", str(tmp_path / "t.db"))
    with TestClient(app) as client:
        current = client.get("/api/v1/sessions/current").json()
        assert current["status"] == "active"

        app.state.bridge.process_telemetry(_telemetry(events=[{
            "event_type": "YAWNING", "started_at": "2026-10-05T08:00:00+00:00",
            "duration_ms": 2000, "risk_score": 40.0, "risk_level": "WARNING",
            "confidence": 0.9, "reason": "test",
        }]))

        # chỉ lấy sự kiện của phiên hiện tại
        scoped = client.get("/api/v1/events", params={"session_id": current["id"]}).json()["events"]
        assert len(scoped) == 1 and scoped[0]["event_type"] == "YAWNING"
        assert client.get("/api/v1/events", params={"session_id": "khong-co"}).json()["events"] == []

        stopped = client.post("/api/v1/sessions/stop").json()
        assert stopped["stopped"]["status"] == "COMPLETED"
        assert stopped["stopped"]["event_count"] == 1
        assert stopped["stopped"]["max_risk"] == 40.0
        assert stopped["current"]["id"] != current["id"]

        # phiên mới nhận sự kiện tiếp theo, phiên cũ giữ nguyên
        app.state.bridge.process_telemetry(_telemetry(events=[{
            "event_type": "LOOKING_AWAY", "started_at": "2026-10-05T08:01:00+00:00",
            "duration_ms": 2000, "risk_score": 60.0, "risk_level": "WARNING",
            "confidence": 0.9, "reason": "test",
        }]))
        assert len(client.get("/api/v1/events", params={"session_id": stopped["current"]["id"]}).json()["events"]) == 1
        assert len(client.get("/api/v1/events", params={"session_id": current["id"]}).json()["events"]) == 1

        listed = client.get("/api/v1/sessions").json()["sessions"]
        assert len(listed) == 2
        assert client.get(f"/api/v1/sessions/{current['id']}").json()["event_count"] == 1
        assert client.get("/api/v1/sessions/khong-co").status_code == 404


def test_calibrate_route_not_shadowed_by_session_detail(tmp_path, monkeypatch):
    monkeypatch.setenv("DRIVERGUARD_DB", str(tmp_path / "t.db"))
    with TestClient(app) as client:
        assert client.post("/api/v1/sessions/calibrate").json() == {"ok": True}


def test_su_kien_duoc_gan_anh_va_tai_duoc_qua_api(tmp_path, monkeypatch):
    from app.services.snapshot_store import SnapshotStore

    monkeypatch.setenv("DRIVERGUARD_DB", str(tmp_path / "t.db"))
    jpeg = b"\xff\xd8\xff" + b"z" * 300
    with TestClient(app) as client:
        app.state.bridge.snapshots = SnapshotStore(tmp_path / "snaps")
        app.state.bridge.frame = jpeg
        app.state.bridge.process_telemetry(_telemetry(events=[{
            "event_type": "DROWSINESS_ACUTE", "started_at": "2026-10-05T08:00:00+00:00",
            "duration_ms": 1800, "risk_score": 90.0, "risk_level": "DANGER",
            "confidence": 0.9, "reason": "test",
        }]))

        event = client.get("/api/v1/events").json()["events"][0]
        assert event["snapshot_path"]

        response = client.get(f"/api/v1/events/{event['id']}/snapshot")
        assert response.status_code == 200
        assert response.headers["content-type"] == "image/jpeg"
        assert response.content == jpeg

        assert client.get("/api/v1/events/khong-co/snapshot").status_code == 404


def test_su_kien_van_duoc_ghi_khi_chua_co_khung_hinh(tmp_path, monkeypatch):
    from app.services.snapshot_store import SnapshotStore

    monkeypatch.setenv("DRIVERGUARD_DB", str(tmp_path / "t.db"))
    with TestClient(app) as client:
        app.state.bridge.snapshots = SnapshotStore(tmp_path / "snaps")
        app.state.bridge.frame = None
        app.state.bridge.process_telemetry(_telemetry(events=[{
            "event_type": "YAWNING", "started_at": "2026-10-05T08:00:00+00:00",
            "duration_ms": 2000, "risk_score": 40.0, "risk_level": "WARNING",
            "confidence": 0.9, "reason": "test",
        }]))

        event = client.get("/api/v1/events").json()["events"][0]
        assert event["event_type"] == "YAWNING"
        assert event["snapshot_path"] is None
        assert client.get(f"/api/v1/events/{event['id']}/snapshot").status_code == 404
