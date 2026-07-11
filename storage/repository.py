"""
storage/repository.py

CRUD repositories for each database table.
Each repository takes a Database instance and exposes typed methods.

Usage:
    from storage.database import Database
    from storage.repository import EventRepo, LogRepo, SettingRepo, NotificationRepo

    db = Database()
    db.init_db()

    events = EventRepo(db)
    events.insert(pin=17, event_type="button_pressed", source="gpio")

    logs = LogRepo(db)
    logs.insert(level="INFO", message="System started", source="core.app")
"""

import sqlite3
from datetime import datetime
from typing import Optional

from storage.database import Database
from storage.models import Event, Log, Setting, Notification


def _row_to_dict(row: sqlite3.Row) -> dict:
    return dict(row)


# ──────────────────────────────────────────────────────────────────────────────
# Event Repository
# ──────────────────────────────────────────────────────────────────────────────

class EventRepo:
    """CRUD for the `events` table."""

    def __init__(self, db: Database):
        self._db = db

    def insert(
        self,
        pin: int,
        event_type: str,
        source: str = "gpio",
        notes: str = "",
        timestamp: Optional[str] = None,
    ) -> int:
        """Insert a new event. Returns the new row id."""
        ts = timestamp or datetime.utcnow().isoformat()
        conn = self._db.get_conn()
        cur = conn.execute(
            """
            INSERT INTO events (pin, event_type, source, notes, timestamp)
            VALUES (?, ?, ?, ?, ?)
            """,
            (pin, event_type, source, notes, ts),
        )
        conn.commit()
        return cur.lastrowid

    def get_all(self, limit: int = 100) -> list[dict]:
        """Fetch the most recent events, newest first."""
        conn = self._db.get_conn()
        rows = conn.execute(
            "SELECT * FROM events ORDER BY id DESC LIMIT ?", (limit,)
        ).fetchall()
        return [_row_to_dict(r) for r in rows]

    def get_by_pin(self, pin: int, limit: int = 50) -> list[dict]:
        """Fetch events for a specific GPIO pin."""
        conn = self._db.get_conn()
        rows = conn.execute(
            "SELECT * FROM events WHERE pin = ? ORDER BY id DESC LIMIT ?",
            (pin, limit),
        ).fetchall()
        return [_row_to_dict(r) for r in rows]

    def get_by_type(self, event_type: str, limit: int = 50) -> list[dict]:
        """Fetch events filtered by type."""
        conn = self._db.get_conn()
        rows = conn.execute(
            "SELECT * FROM events WHERE event_type = ? ORDER BY id DESC LIMIT ?",
            (event_type, limit),
        ).fetchall()
        return [_row_to_dict(r) for r in rows]

    def count(self) -> int:
        """Total number of events stored."""
        conn = self._db.get_conn()
        return conn.execute("SELECT COUNT(*) FROM events").fetchone()[0]

    def clear(self) -> None:
        """Delete all events (useful for testing / reset)."""
        conn = self._db.get_conn()
        conn.execute("DELETE FROM events")
        conn.commit()


# ──────────────────────────────────────────────────────────────────────────────
# Log Repository
# ──────────────────────────────────────────────────────────────────────────────

class LogRepo:
    """CRUD for the `logs` table."""

    LEVELS = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}

    def __init__(self, db: Database):
        self._db = db

    def insert(
        self,
        message: str,
        level: str = "INFO",
        source: str = "",
        timestamp: Optional[str] = None,
    ) -> int:
        """Insert a log entry. Returns the new row id."""
        level = level.upper()
        if level not in self.LEVELS:
            level = "INFO"
        ts = timestamp or datetime.utcnow().isoformat()
        conn = self._db.get_conn()
        cur = conn.execute(
            """
            INSERT INTO logs (level, message, source, timestamp)
            VALUES (?, ?, ?, ?)
            """,
            (level, message, source, ts),
        )
        conn.commit()
        return cur.lastrowid

    def get_all(self, limit: int = 200) -> list[dict]:
        """Fetch the most recent log entries, newest first."""
        conn = self._db.get_conn()
        rows = conn.execute(
            "SELECT * FROM logs ORDER BY id DESC LIMIT ?", (limit,)
        ).fetchall()
        return [_row_to_dict(r) for r in rows]

    def get_by_level(self, level: str, limit: int = 100) -> list[dict]:
        """Fetch logs filtered by level."""
        conn = self._db.get_conn()
        rows = conn.execute(
            "SELECT * FROM logs WHERE level = ? ORDER BY id DESC LIMIT ?",
            (level.upper(), limit),
        ).fetchall()
        return [_row_to_dict(r) for r in rows]

    def get_errors(self, limit: int = 50) -> list[dict]:
        """Shortcut: fetch ERROR and CRITICAL logs."""
        conn = self._db.get_conn()
        rows = conn.execute(
            """
            SELECT * FROM logs
            WHERE level IN ('ERROR', 'CRITICAL')
            ORDER BY id DESC LIMIT ?
            """,
            (limit,),
        ).fetchall()
        return [_row_to_dict(r) for r in rows]

    def count(self) -> int:
        """Total number of log entries stored."""
        conn = self._db.get_conn()
        return conn.execute("SELECT COUNT(*) FROM logs").fetchone()[0]


# ──────────────────────────────────────────────────────────────────────────────
# Setting Repository
# ──────────────────────────────────────────────────────────────────────────────

class SettingRepo:
    """CRUD for the `settings` table (key/value store)."""

    def __init__(self, db: Database):
        self._db = db

    def get(self, key: str, default: Optional[str] = None) -> Optional[str]:
        """Retrieve a setting value by key."""
        conn = self._db.get_conn()
        row = conn.execute(
            "SELECT value FROM settings WHERE key = ?", (key,)
        ).fetchone()
        return row["value"] if row else default

    def set(self, key: str, value: str, description: str = "") -> None:
        """Insert or update a setting."""
        ts = datetime.utcnow().isoformat()
        conn = self._db.get_conn()
        conn.execute(
            """
            INSERT INTO settings (key, value, description, updated_at)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(key) DO UPDATE SET
                value      = excluded.value,
                updated_at = excluded.updated_at
            """,
            (key, value, description, ts),
        )
        conn.commit()

    def get_all(self) -> list[dict]:
        """Fetch all settings as a list of dicts."""
        conn = self._db.get_conn()
        rows = conn.execute("SELECT * FROM settings ORDER BY key").fetchall()
        return [_row_to_dict(r) for r in rows]

    def delete(self, key: str) -> None:
        """Remove a setting by key."""
        conn = self._db.get_conn()
        conn.execute("DELETE FROM settings WHERE key = ?", (key,))
        conn.commit()


# ──────────────────────────────────────────────────────────────────────────────
# Notification Repository
# ──────────────────────────────────────────────────────────────────────────────

class NotificationRepo:
    """CRUD for the `notifications` table."""

    STATUSES = {"pending", "sent", "failed"}

    def __init__(self, db: Database):
        self._db = db

    def insert(
        self,
        title: str,
        body: str = "",
        channel: str = "system",
        status: str = "pending",
        timestamp: Optional[str] = None,
    ) -> int:
        """Queue a new notification. Returns the new row id."""
        ts = timestamp or datetime.utcnow().isoformat()
        conn = self._db.get_conn()
        cur = conn.execute(
            """
            INSERT INTO notifications (title, body, channel, status, timestamp)
            VALUES (?, ?, ?, ?, ?)
            """,
            (title, body, channel, status, ts),
        )
        conn.commit()
        return cur.lastrowid

    def update_status(self, notification_id: int, status: str) -> None:
        """Update the delivery status of a notification."""
        if status not in self.STATUSES:
            raise ValueError(f"Invalid status: {status!r}. Use {self.STATUSES}")
        conn = self._db.get_conn()
        conn.execute(
            "UPDATE notifications SET status = ? WHERE id = ?",
            (status, notification_id),
        )
        conn.commit()

    def get_pending(self) -> list[dict]:
        """Fetch all unsent notifications."""
        conn = self._db.get_conn()
        rows = conn.execute(
            "SELECT * FROM notifications WHERE status = 'pending' ORDER BY id ASC"
        ).fetchall()
        return [_row_to_dict(r) for r in rows]

    def get_all(self, limit: int = 100) -> list[dict]:
        """Fetch recent notifications, newest first."""
        conn = self._db.get_conn()
        rows = conn.execute(
            "SELECT * FROM notifications ORDER BY id DESC LIMIT ?", (limit,)
        ).fetchall()
        return [_row_to_dict(r) for r in rows]

    def count_by_status(self, status: str) -> int:
        """Count notifications by status."""
        conn = self._db.get_conn()
        return conn.execute(
            "SELECT COUNT(*) FROM notifications WHERE status = ?", (status,)
        ).fetchone()[0]
