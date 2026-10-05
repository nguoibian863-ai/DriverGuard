import asyncio
import multiprocessing
import os
import queue
import sys
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from app.db.database import create_session, end_session, list_events
from app.services.telemetry_bridge import TelemetryBridge
from app.services.websocket_service import ConnectionManager

# Cho phép import package `ai` (nằm ở thư mục gốc dự án) dù chạy uvicorn từ apps/backend
ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


class MuteRequest(BaseModel):
    duration_seconds: int = Field(gt=0)


@asynccontextmanager
async def lifespan(app: FastAPI):
    context = multiprocessing.get_context("spawn")
    start_worker = os.getenv("DRIVERGUARD_START_WORKER", "1") != "0"
    app.state.telemetry_q = context.Queue() if start_worker else queue.Queue()
    app.state.command_q = context.Queue() if start_worker else queue.Queue()
    app.state.frame_q = context.Queue(maxsize=2) if start_worker else queue.Queue(maxsize=2)
    app.state.manager = ConnectionManager()
    app.state.worker = None
    app.state.session = create_session()
    app.state.bridge = TelemetryBridge(
        app.state.telemetry_q, app.state.frame_q, app.state.manager, asyncio.get_running_loop(), app.state.session["id"]
    )
    app.state.bridge.start()
    if start_worker:
        from ai.runtime.worker import run_worker
        config = {"simulate": os.getenv("DRIVERGUARD_SIMULATE", "0") == "1", "camera_index": 0, "enable_phone": True}
        app.state.worker = context.Process(target=run_worker, args=(app.state.telemetry_q, app.state.command_q, app.state.frame_q, config), daemon=True)
        app.state.worker.start()
    try:
        yield
    finally:
        if app.state.worker is not None:
            app.state.command_q.put({"cmd": "stop"})
            app.state.worker.join(timeout=3)
            if app.state.worker.is_alive():
                app.state.worker.terminate()
                app.state.worker.join(timeout=1)
        app.state.bridge.stop()
        end_session(app.state.session["id"])


app = FastAPI(title="DriverGuard API", version="0.1.0", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["http://localhost:3000"], allow_methods=["*"], allow_headers=["*"])


@app.get("/api/v1/health")
def health():
    worker = app.state.worker
    bridge = app.state.bridge
    alive = worker is not None and worker.is_alive()
    recent = bridge.recent()
    telemetry = bridge.telemetry or {}
    camera_ok = recent and telemetry.get("error") != "camera_unavailable"
    return {"status": "ok" if alive and recent else "degraded", "ai_worker_alive": alive, "camera_connected": camera_ok}


@app.websocket("/ws/status")
async def status_socket(websocket: WebSocket):
    manager = app.state.manager
    await manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)


@app.get("/api/v1/video/stream")
async def video_stream(overlay: bool = True):
    async def frames():
        previous = None
        while True:
            frame = app.state.bridge.latest_frame()
            if frame is not None and frame is not previous:
                previous = frame
                yield b"--frame\r\nContent-Type: image/jpeg\r\n\r\n" + frame + b"\r\n"
            await asyncio.sleep(0.05)
    return StreamingResponse(frames(), media_type="multipart/x-mixed-replace; boundary=frame")


@app.post("/api/v1/sessions/calibrate")
def calibrate():
    app.state.command_q.put({"cmd": "calibrate"})
    return {"ok": True}


@app.post("/api/v1/alerts/mute")
def mute(body: MuteRequest):
    app.state.command_q.put({"cmd": "mute", "duration_seconds": body.duration_seconds})
    return {"ok": True}


@app.get("/api/v1/events")
def events(limit: int = 50):
    return {"events": list_events(max(0, min(limit, 1000)))}


@app.get("/api/v1/config")
def config():
    from dataclasses import asdict

    from ai.runtime.thresholds import load_thresholds

    return {
        "simulate": os.getenv("DRIVERGUARD_SIMULATE", "0") == "1",
        "camera_index": 0,
        "enable_phone": True,
        "thresholds": asdict(load_thresholds()),
    }
