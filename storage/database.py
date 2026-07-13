"""
storage/database.py

SQLite database for Octizen.
Single source of truth. Tables: logs, queue.

DB path: storage/octizen.db (auto-created on first run)
"""

import sqlite3
from datetime import datetime
from pathlib import Path
from core.logger import logger


DB_PATH = Path(__file__).resolve().parent / "octizen.db"


class Database:
    """
    Manages the SQLite connection, schema, and log operations.
    """

    def __init__(self, db_path: str | Path = DB_PATH):
        self.db_path = Path(db_path)
        self._conn: sqlite3.Connection | None = None

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def init_db(self) -> None:
        """Open connection and create tables. Call once at startup."""
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(
            str(self.db_path),
            check_same_thread=False,
            detect_types=sqlite3.PARSE_DECLTYPES,
        )
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA journal_mode=WAL;")
        self._conn.execute("PRAGMA foreign_keys=ON;")
        self._create_tables()
        logger.info(f"[DB] Connected → {self.db_path}")

    def get_conn(self) -> sqlite3.Connection:
        """Returns the active connection. Raises if not initialised."""
        if self._conn is None:
            raise RuntimeError("Database not initialised. Call init_db() first.")
        return self._conn

    def close(self) -> None:
        """Commit pending writes and close the connection."""
        if self._conn:
            self._conn.commit()
            self._conn.close()
            self._conn = None
            logger.info("[DB] Connection closed.")

    # ------------------------------------------------------------------
    # Schema
    # ------------------------------------------------------------------

    def _create_tables(self) -> None:
        """Creates all tables if they do not already exist."""
        conn = self.get_conn()
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS logs (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                event      TEXT    NOT NULL,
                created_at TEXT    NOT NULL DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS queue (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                task_type    TEXT    NOT NULL,
                payload      TEXT             DEFAULT '',
                status       TEXT    NOT NULL DEFAULT 'pending',
                priority     INTEGER NOT NULL DEFAULT 0,
                created_at   TEXT    NOT NULL DEFAULT (datetime('now')),
                started_at   TEXT,
                completed_at TEXT,
                retry_count  INTEGER NOT NULL DEFAULT 0,
                error        TEXT
            );
        """)
        conn.commit()
        logger.info("[DB] Tables verified.")

    # ------------------------------------------------------------------
    # Log operations
    # ------------------------------------------------------------------

    def log_event(self, event: str) -> int:
        """
        Insert a log row. Returns the new row id.
        This is the ONLY write method — every event in the system
        flows through here via EventManager.emit().
        """
        conn = self.get_conn()
        cur = conn.execute(
            "INSERT INTO logs (event, created_at) VALUES (?, ?)",
            (event, datetime.utcnow().isoformat()),
        )
        conn.commit()
        row_id = cur.lastrowid
        logger.info(f"[DB] Logged: id={row_id} event={event}")
        return row_id

    def get_logs(self, limit: int = 100) -> list[dict]:
        """Fetch recent log entries, newest first."""
        conn = self.get_conn()
        rows = conn.execute(
            "SELECT * FROM logs ORDER BY id DESC LIMIT ?", (limit,)
        ).fetchall()
        return [dict(r) for r in rows]
