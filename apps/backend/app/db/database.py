import os
import sqlite3
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4


def _connect():
    path = Path(os.getenv("DRIVERGUARD_DB", "data/driverguard.db"))
    path.parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(path)
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA foreign_keys = ON")
    db.execute("CREATE TABLE IF NOT EXISTS sessions (id TEXT PRIMARY KEY, started_at TEXT, ended_at TEXT, status TEXT, neutral_yaw REAL, neutral_pitch REAL, event_count INTEGER, average_risk REAL, max_risk REAL)")
    db.execute("CREATE TABLE IF NOT EXISTS events (id TEXT PRIMARY KEY, session_id TEXT, event_type TEXT, started_at TEXT, ended_at TEXT, duration_ms INTEGER, risk_score REAL, risk_level TEXT, confidence REAL, reason TEXT, snapshot_path TEXT, FOREIGN KEY(session_id) REFERENCES sessions(id))")
    db.commit()
    return db


def create_session(session=None):
    session = dict(session or {})
    session.setdefault("id", str(uuid4()))
    session.setdefault("started_at", datetime.now(UTC).isoformat())
    session.setdefault("status", "active")
    session.setdefault("event_count", 0)
    keys = ("id", "started_at", "ended_at", "status", "neutral_yaw", "neutral_pitch", "event_count", "average_risk", "max_risk")
    with _connect() as db:
        db.execute(f"INSERT INTO sessions ({','.join(keys)}) VALUES ({','.join(':'+key for key in keys)})", {key: session.get(key) for key in keys})
    return session


def insert_event(event, session_id=None):
    event = dict(event)
    event.setdefault("id", str(uuid4()))
    event.setdefault("session_id", session_id)
    keys = ("id", "session_id", "event_type", "started_at", "ended_at", "duration_ms", "risk_score", "risk_level", "confidence", "reason", "snapshot_path")
    with _connect() as db:
        db.execute(f"INSERT INTO events ({','.join(keys)}) VALUES ({','.join(':'+key for key in keys)})", {key: event.get(key) for key in keys})
        if event["session_id"]:
            db.execute("UPDATE sessions SET event_count = event_count + 1 WHERE id = ?", (event["session_id"],))
    return event


def list_events(limit=50, session_id=None):
    query = "SELECT id, session_id, event_type, started_at, duration_ms, risk_score, risk_level, confidence, reason, snapshot_path FROM events"
    params = []
    if session_id:
        query += " WHERE session_id = ?"
        params.append(session_id)
    with _connect() as db:
        rows = db.execute(query + " ORDER BY started_at DESC, rowid DESC LIMIT ?", (*params, limit)).fetchall()
    return [dict(row) for row in rows]


def list_sessions(limit=50):
    with _connect() as db:
        rows = db.execute("SELECT * FROM sessions ORDER BY started_at DESC, rowid DESC LIMIT ?", (limit,)).fetchall()
    return [dict(row) for row in rows]


def get_session(session_id):
    with _connect() as db:
        row = db.execute("SELECT * FROM sessions WHERE id = ?", (session_id,)).fetchone()
    return dict(row) if row else None


def get_event(event_id):
    with _connect() as db:
        row = db.execute("SELECT * FROM events WHERE id = ?", (event_id,)).fetchone()
    return dict(row) if row else None


def end_session(session_id):
    """Đóng phiên và tổng hợp số sự kiện, rủi ro trung bình/lớn nhất từ bảng events."""
    with _connect() as db:
        stats = db.execute(
            "SELECT COUNT(*) AS n, AVG(risk_score) AS avg_risk, MAX(risk_score) AS max_risk FROM events WHERE session_id = ?",
            (session_id,),
        ).fetchone()
        db.execute(
            "UPDATE sessions SET ended_at = ?, status = 'COMPLETED', event_count = ?, average_risk = ?, max_risk = ? WHERE id = ?",
            (datetime.now(UTC).isoformat(), stats["n"], stats["avg_risk"], stats["max_risk"], session_id),
        )
