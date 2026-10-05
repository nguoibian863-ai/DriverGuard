import asyncio
import queue
import threading
import time

from app.db.database import insert_event


class TelemetryBridge:
    def __init__(self, telemetry_q, frame_q, manager, loop, session_id=None):
        self.telemetry_q = telemetry_q
        self.frame_q = frame_q
        self.manager = manager
        self.loop = loop
        self.session_id = session_id
        self.telemetry = None
        self.frame = None
        self.last_telemetry_at = None
        self._stop = threading.Event()
        self._lock = threading.Lock()
        self._thread = None

    def start(self):
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self):
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=2)

    def _run(self):
        while not self._stop.is_set():
            try:
                telemetry = self.telemetry_q.get(timeout=0.05)
            except queue.Empty:
                telemetry = None
            if telemetry is not None:
                self.process_telemetry(telemetry)
            while True:
                try:
                    frame = self.frame_q.get_nowait()
                except queue.Empty:
                    break
                with self._lock:
                    self.frame = frame

    def process_telemetry(self, telemetry):
        with self._lock:
            self.telemetry = telemetry
            self.last_telemetry_at = time.monotonic()
        for event in telemetry.get("events", []):
            insert_event(event, self.session_id)
        asyncio.run_coroutine_threadsafe(self.manager.broadcast(telemetry), self.loop)

    def latest_frame(self):
        with self._lock:
            return self.frame

    def recent(self, seconds=5):
        with self._lock:
            return self.last_telemetry_at is not None and time.monotonic() - self.last_telemetry_at < seconds
