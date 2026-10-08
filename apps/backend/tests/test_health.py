import os

from fastapi.testclient import TestClient

os.environ["DRIVERGUARD_START_WORKER"] = "0"
from app.db.database import insert_event
from app.main import app


def test_backend(tmp_path, monkeypatch):
    monkeypatch.setenv("DRIVERGUARD_DB", str(tmp_path / "driverguard.db"))
    with TestClient(app) as client:
        response = client.get("/api/v1/health")
        assert response.status_code == 200
        assert response.json() == {"status": "degraded", "ai_worker_alive": False, "camera_connected": False}

        insert_event({"event_type": "LOOKING_AWAY", "started_at": "2026-10-05T08:00:00+00:00", "duration_ms": 1800, "risk_score": 85, "risk_level": "DANGER", "confidence": .9, "reason": "test"})
        events = client.get("/api/v1/events").json()["events"]
        assert len(events) == 1 and events[0]["event_type"] == "LOOKING_AWAY"

        assert client.post("/api/v1/sessions/calibrate").json() == {"ok": True}
        assert app.state.command_q.get(timeout=2) == {"cmd": "calibrate"}
        assert client.post("/api/v1/alerts/mute", json={"duration_seconds": 15}).json() == {"ok": True}
        assert app.state.command_q.get(timeout=2) == {"cmd": "mute", "duration_seconds": 15}

        with client.websocket_connect("/ws/status") as ws:
            telemetry = {"timestamp": "2026-10-05T08:00:01+00:00", "face_detected": True, "events": []}
            app.state.telemetry_q.put(telemetry)
            assert ws.receive_json() == telemetry
