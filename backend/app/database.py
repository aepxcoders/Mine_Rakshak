import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

DB_PATH = Path(__file__).resolve().parent.parent / "mine_rescue_test.db"


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _connect():
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    return connection


def _init_db():
    with _connect() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS telemetry (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                rover_id TEXT NOT NULL,
                received_at TEXT NOT NULL,
                payload_json TEXT NOT NULL,
                hazard_json TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_telemetry_rover_time
            ON telemetry (rover_id, received_at DESC)
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                rover_id TEXT NOT NULL,
                event_type TEXT NOT NULL,
                message TEXT NOT NULL,
                severity TEXT NOT NULL,
                details_json TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_events_rover_time
            ON events (rover_id, created_at DESC)
            """
        )


_init_db()


def _parse_datetime(value: str | None):
    if not value:
        return None
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None


def db_ok() -> bool:
    try:
        with _connect() as conn:
            conn.execute("SELECT 1").fetchone()
        return True
    except sqlite3.Error:
        return False


def save_telemetry(telemetry: dict[str, Any], hazard: dict[str, Any]) -> dict[str, Any]:
    received_at = utc_now()
    rover_id = telemetry.get("rover_id", "MRR-01")
    with _connect() as conn:
        cursor = conn.execute(
            """
            INSERT INTO telemetry (rover_id, received_at, payload_json, hazard_json)
            VALUES (?, ?, ?, ?)
            """,
            (
                rover_id,
                received_at.isoformat(),
                json.dumps(telemetry, separators=(",", ":")),
                json.dumps(hazard, separators=(",", ":")),
            ),
        )
        row_id = cursor.lastrowid

    document = dict(telemetry)
    document["_id"] = str(row_id)
    document["hazard"] = hazard
    document["received_at"] = received_at
    return document


def latest_telemetry(rover_id: str | None = None):
    sql = "SELECT * FROM telemetry"
    params: tuple[Any, ...] = ()
    if rover_id:
        sql += " WHERE rover_id = ?"
        params = (rover_id,)
    sql += " ORDER BY received_at DESC LIMIT 1"

    with _connect() as conn:
        row = conn.execute(sql, params).fetchone()
    if row is None:
        return None

    document = json.loads(row["payload_json"])
    document["_id"] = str(row["id"])
    document["hazard"] = json.loads(row["hazard_json"])
    document["received_at"] = _parse_datetime(row["received_at"])
    return document



def recent_telemetry(limit: int = 60, rover_id: str | None = None):
    """Return recent telemetry payloads oldest-to-newest for trend analysis."""
    sql = "SELECT * FROM telemetry"
    params: list[Any] = []
    if rover_id:
        sql += " WHERE rover_id = ?"
        params.append(rover_id)
    sql += " ORDER BY received_at DESC LIMIT ?"
    params.append(limit)

    with _connect() as conn:
        rows = conn.execute(sql, tuple(params)).fetchall()

    documents = []
    for row in reversed(rows):
        document = json.loads(row["payload_json"])
        document["_id"] = str(row["id"])
        document["hazard"] = json.loads(row["hazard_json"])
        document["received_at"] = _parse_datetime(row["received_at"])
        documents.append(document)
    return documents


def _event_from_row(row):
    if row is None:
        return None
    return {
        "_id": str(row["id"]),
        "rover_id": row["rover_id"],
        "type": row["event_type"],
        "message": row["message"],
        "severity": row["severity"],
        "details": json.loads(row["details_json"]),
        "created_at": _parse_datetime(row["created_at"]),
    }


def latest_event(rover_id: str | None = None):
    sql = "SELECT * FROM events"
    params: tuple[Any, ...] = ()
    if rover_id:
        sql += " WHERE rover_id = ?"
        params = (rover_id,)
    sql += " ORDER BY created_at DESC LIMIT 1"
    with _connect() as conn:
        row = conn.execute(sql, params).fetchone()
    return _event_from_row(row)


def recent_events(limit: int = 50, rover_id: str | None = None):
    sql = "SELECT * FROM events"
    params: list[Any] = []
    if rover_id:
        sql += " WHERE rover_id = ?"
        params.append(rover_id)
    sql += " ORDER BY created_at DESC LIMIT ?"
    params.append(limit)
    with _connect() as conn:
        rows = conn.execute(sql, tuple(params)).fetchall()
    return [_event_from_row(row) for row in rows]


def log_event(
    rover_id: str,
    event_type: str,
    message: str,
    severity: str = "info",
    details: dict[str, Any] | None = None,
):
    created_at = utc_now()
    details = details or {}
    with _connect() as conn:
        cursor = conn.execute(
            """
            INSERT INTO events (rover_id, event_type, message, severity, details_json, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                rover_id,
                event_type,
                message,
                severity,
                json.dumps(details, separators=(",", ":")),
                created_at.isoformat(),
            ),
        )
        row_id = cursor.lastrowid

    return {
        "_id": str(row_id),
        "rover_id": rover_id,
        "type": event_type,
        "message": message,
        "severity": severity,
        "details": details,
        "created_at": created_at,
    }


def should_log_hazard(rover_id: str, hazard: dict[str, Any]) -> bool:
    with _connect() as conn:
        row = conn.execute(
            """
            SELECT details_json FROM events
            WHERE rover_id = ? AND event_type = 'hazard'
            ORDER BY created_at DESC LIMIT 1
            """,
            (rover_id,),
        ).fetchone()

    if row is None:
        return True

    previous = json.loads(row["details_json"])

    # Sensor values fluctuate every packet, so reason strings can change by a
    # decimal even when the actual hazard state has not changed. Log state
    # transitions rather than creating a new event every telemetry cycle.
    return previous.get("state") != hazard.get("state")
