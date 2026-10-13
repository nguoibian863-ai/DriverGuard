"""Kiểm thử đầu-cuối: chạy uvicorn thật với AI worker ở chế độ mô phỏng, không cần camera.

Bao phủ: worker tiến trình con sống, telemetry qua WebSocket, sự kiện lưu vào SQLite đúng phiên,
luồng MJPEG trả khung JPEG, và vòng đời phiên (stop/list/detail).

Chạy: python -m pytest tests/integration -q (từ thư mục gốc dự án).
"""

import json
import os
import socket
import subprocess
import sys
import time
from pathlib import Path

import pytest

httpx = pytest.importorskip("httpx")
pytest.importorskip("uvicorn")
pytest.importorskip("cv2")

ROOT = Path(__file__).resolve().parents[2]
BACKEND = ROOT / "apps" / "backend"
STARTUP_TIMEOUT_S = 90.0


def _free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


@pytest.fixture(scope="module")
def server(tmp_path_factory):
    """Khởi động uvicorn trong tiến trình riêng; worker chạy kịch bản mô phỏng."""
    port = _free_port()
    workdir = tmp_path_factory.mktemp("db")
    env = {
        **os.environ,
        "DRIVERGUARD_DB": str(workdir / "e2e.db"),
        "DRIVERGUARD_SNAPSHOT_DIR": str(workdir / "snapshots"),
        "DRIVERGUARD_SIMULATE": "1",
        "DRIVERGUARD_START_WORKER": "1",
        "PYTHONPATH": os.pathsep.join([str(ROOT), str(BACKEND)]),
    }
    process = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", str(port), "--log-level", "warning"],
        cwd=BACKEND, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
    )
    base = f"http://127.0.0.1:{port}"
    try:
        deadline = time.monotonic() + STARTUP_TIMEOUT_S
        while time.monotonic() < deadline:
            if process.poll() is not None:
                pytest.fail(f"uvicorn thoát sớm:\n{process.stdout.read()}")
            try:
                # "ok" = worker sống VÀ telemetry đã chảy; chờ mốc này để test không gặp đua
                if httpx.get(f"{base}/api/v1/health", timeout=2.0).json()["status"] == "ok":
                    break
            except Exception:
                pass
            time.sleep(0.5)
        else:
            process.kill()
            pytest.fail("backend không vào trạng thái ok trong thời gian chờ")
        yield base, port
    finally:
        process.terminate()
        try:
            process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            process.kill()


def _wait(predicate, timeout=60.0, interval=1.0):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        value = predicate()
        if value:
            return value
        time.sleep(interval)
    return None


def test_health_va_config(server):
    base, _ = server
    health = httpx.get(f"{base}/api/v1/health", timeout=5.0).json()
    assert health == {"status": "ok", "ai_worker_alive": True, "camera_connected": True}

    config = httpx.get(f"{base}/api/v1/config", timeout=5.0).json()
    assert config["simulate"] is True
    assert config["thresholds"]["ear_threshold"] > 0


def test_websocket_day_telemetry(server):
    """Telemetry phải tới qua WebSocket với đủ trường rủi ro và tín hiệu."""
    websockets = pytest.importorskip("websockets.sync.client")
    _, port = server
    with websockets.connect(f"ws://127.0.0.1:{port}/ws/status", open_timeout=15) as ws:
        messages = [json.loads(ws.recv(timeout=15)) for _ in range(3)]

    for message in messages:
        assert set(message) >= {"timestamp", "risk_score", "risk_level", "ear", "mar", "fps", "pose", "events"}
        assert 0.0 <= message["risk_score"] <= 100.0
        assert message["risk_level"] in {"NORMAL", "WARNING", "DANGER"}
        assert isinstance(message["face_detected"], bool)


def test_kich_ban_sinh_su_kien_va_gan_dung_phien(server):
    """Kịch bản mô phỏng (nhắm mắt/quay đầu/điện thoại/ngáp) lặp 40 s phải sinh sự kiện."""
    base, _ = server
    session_id = httpx.get(f"{base}/api/v1/sessions/current", timeout=5.0).json()["id"]

    events = _wait(lambda: httpx.get(f"{base}/api/v1/events", timeout=5.0).json()["events"], timeout=75.0)
    assert events, "không sinh được sự kiện nào từ kịch bản mô phỏng"

    for event in events:
        assert event["session_id"] == session_id
        assert event["risk_level"] in {"NORMAL", "WARNING", "DANGER"}
        assert event["duration_ms"] > 0

    assert {e["event_type"] for e in events} & {"DROWSINESS_ACUTE", "YAWNING", "LOOKING_AWAY", "PHONE_USAGE"}

    scoped = httpx.get(f"{base}/api/v1/events", params={"session_id": session_id}, timeout=5.0).json()["events"]
    assert len(scoped) == len(events)
    assert httpx.get(f"{base}/api/v1/events", params={"session_id": "khong-ton-tai"}, timeout=5.0).json()["events"] == []


def test_su_kien_co_anh_chup_tai_duoc(server):
    """Sự kiện sinh ra khi worker đang chạy phải kèm ảnh JPEG tải được qua API."""
    base, _ = server
    events = _wait(lambda: httpx.get(f"{base}/api/v1/events", timeout=5.0).json()["events"], timeout=75.0)
    assert events, "không sinh được sự kiện nào"

    with_snapshot = [e for e in events if e.get("snapshot_path")]
    assert with_snapshot, "không sự kiện nào được gắn ảnh chụp"

    response = httpx.get(f"{base}/api/v1/events/{with_snapshot[0]['id']}/snapshot", timeout=10.0)
    assert response.status_code == 200
    assert response.headers["content-type"] == "image/jpeg"
    assert response.content.startswith(b"\xff\xd8\xff")

    assert httpx.get(f"{base}/api/v1/events/khong-ton-tai/snapshot", timeout=5.0).status_code == 404


def test_mjpeg_tra_ve_khung_jpeg(server):
    base, _ = server
    with httpx.stream("GET", f"{base}/api/v1/video/stream", timeout=20.0) as response:
        assert response.status_code == 200
        assert "multipart/x-mixed-replace" in response.headers["content-type"]
        buffer = b""
        for chunk in response.iter_bytes():
            buffer += chunk
            if b"\xff\xd8\xff" in buffer and len(buffer) > 4000:
                break
    assert b"Content-Type: image/jpeg" in buffer
    assert b"\xff\xd8\xff" in buffer  # SOI của JPEG


def test_calibrate_va_mute_khong_loi(server):
    base, _ = server
    assert httpx.post(f"{base}/api/v1/sessions/calibrate", timeout=5.0).json() == {"ok": True}
    assert httpx.post(f"{base}/api/v1/alerts/mute", json={"duration_seconds": 5}, timeout=5.0).json() == {"ok": True}
    assert httpx.post(f"{base}/api/v1/alerts/mute", json={"duration_seconds": 0}, timeout=5.0).status_code == 422


def test_vong_doi_phien(server):
    """Dừng phiên phải chốt thống kê và chuyển sự kiện sau đó sang phiên mới."""
    base, _ = server
    old_id = httpx.get(f"{base}/api/v1/sessions/current", timeout=5.0).json()["id"]
    stopped = httpx.post(f"{base}/api/v1/sessions/stop", timeout=10.0).json()

    assert stopped["stopped"]["id"] == old_id
    assert stopped["stopped"]["status"] == "COMPLETED"
    assert stopped["stopped"]["ended_at"]
    assert stopped["current"]["id"] != old_id

    sessions = httpx.get(f"{base}/api/v1/sessions", timeout=5.0).json()["sessions"]
    assert {s["id"] for s in sessions} >= {old_id, stopped["current"]["id"]}
    assert httpx.get(f"{base}/api/v1/sessions/khong-ton-tai", timeout=5.0).status_code == 404

    detail = httpx.get(f"{base}/api/v1/sessions/{old_id}", timeout=5.0).json()
    assert detail["event_count"] == len(
        httpx.get(f"{base}/api/v1/events", params={"session_id": old_id, "limit": 1000}, timeout=5.0).json()["events"]
    )
