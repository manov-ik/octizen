"""
storage/database_manager.py

The ONLY class that knows sqlite3 exists.
Every other module calls DatabaseManager methods — never raw SQL.

Tables: logs, notes, memories, queue

Usage:
    db = DatabaseManager()
    db.init_db()
    db.save_log("button.pressed (pin=17)")
    db.save_note("Meeting at 3pm", "Discuss project timeline")
    db.save_memory("User prefers dark mode", source="llm", tags="preference")
    db.close()
"""

import sqlite3
from datetime import datetime
from pathlib import Path
from core.logger import logger


DB_PATH = Path(__file__).resolve().parent / "octizen.db"


class DatabaseManager:
    """
    Single gateway to SQLite. Nobody else imports sqlite3.
    """

    def __init__(self, db_path: str | Path = DB_PATH):
        self.db_path = Path(db_path)
        self._conn: sqlite3.Connection | None = None

    # ==================================================================
    # Lifecycle
    # ==================================================================

    def init_db(self) -> None:
        """Open connection and create all tables. Call once at startup."""
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

    def close(self) -> None:
        """Commit pending writes and close the connection."""
        if self._conn:
            self._conn.commit()
            self._conn.close()
            self._conn = None
            logger.info("[DB] Connection closed.")

    # ==================================================================
    # Schema
    # ==================================================================

    def _create_tables(self) -> None:
        """Creates all tables if they do not already exist."""
        self._conn.executescript("""
            -- ── Logs ─────────────────────────────────────────────
            CREATE TABLE IF NOT EXISTS logs (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                event      TEXT    NOT NULL,
                created_at TEXT    NOT NULL DEFAULT (datetime('now'))
            );

            -- ── Notes ────────────────────────────────────────────
            CREATE TABLE IF NOT EXISTS notes (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                title      TEXT    NOT NULL DEFAULT '',
                content    TEXT    NOT NULL DEFAULT '',
                created_at TEXT    NOT NULL DEFAULT (datetime('now'))
            );

            -- ── Memories ─────────────────────────────────────────
            CREATE TABLE IF NOT EXISTS memories (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                content    TEXT    NOT NULL,
                source     TEXT    NOT NULL DEFAULT '',
                tags       TEXT             DEFAULT '',
                created_at TEXT    NOT NULL DEFAULT (datetime('now'))
            );

            -- ── Queue ────────────────────────────────────────────
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

            -- ── Wi-Fi Networks ───────────────────────────────────
            CREATE TABLE IF NOT EXISTS wifi_networks (
                ssid      TEXT PRIMARY KEY,
                password  TEXT NOT NULL,
                priority  INTEGER DEFAULT 0,
                added_at  TEXT NOT NULL DEFAULT (datetime('now'))
            );
        """)
        self._conn.commit()
        logger.info("[DB] Tables verified.")

    # ==================================================================
    # Logs
    # ==================================================================

    def save_log(self, event: str) -> int:
        """Insert a log row. Returns the new row id."""
        cur = self._conn.execute(
            "INSERT INTO logs (event, created_at) VALUES (?, ?)",
            (event, self._now()),
        )
        self._conn.commit()
        row_id = cur.lastrowid
        logger.info(f"[DB] Logged: id={row_id} event={event}")
        return row_id

    def get_logs(self, limit: int = 100) -> list[dict]:
        """Fetch recent log entries, newest first."""
        rows = self._conn.execute(
            "SELECT * FROM logs ORDER BY id DESC LIMIT ?", (limit,)
        ).fetchall()
        return [dict(r) for r in rows]

    # ==================================================================
    # Notes
    # ==================================================================

    def save_note(self, title: str, content: str = "") -> int:
        """Insert a note. Returns the new row id."""
        cur = self._conn.execute(
            "INSERT INTO notes (title, content, created_at) VALUES (?, ?, ?)",
            (title, content, self._now()),
        )
        self._conn.commit()
        row_id = cur.lastrowid
        logger.info(f"[DB] Note saved: id={row_id} title={title}")
        return row_id

    def get_notes(self, limit: int = 100) -> list[dict]:
        """Fetch recent notes, newest first."""
        rows = self._conn.execute(
            "SELECT * FROM notes ORDER BY id DESC LIMIT ?", (limit,)
        ).fetchall()
        return [dict(r) for r in rows]

    def get_note(self, note_id: int) -> dict | None:
        """Fetch a single note by id."""
        row = self._conn.execute(
            "SELECT * FROM notes WHERE id = ?", (note_id,)
        ).fetchone()
        return dict(row) if row else None

    # ==================================================================
    # Memories
    # ==================================================================

    def save_memory(self, content: str, source: str = "", tags: str = "") -> int:
        """Insert a memory. Returns the new row id."""
        cur = self._conn.execute(
            "INSERT INTO memories (content, source, tags, created_at) VALUES (?, ?, ?, ?)",
            (content, source, tags, self._now()),
        )
        self._conn.commit()
        row_id = cur.lastrowid
        logger.info(f"[DB] Memory saved: id={row_id} source={source}")
        return row_id

    def get_memories(self, limit: int = 100) -> list[dict]:
        """Fetch recent memories, newest first."""
        rows = self._conn.execute(
            "SELECT * FROM memories ORDER BY id DESC LIMIT ?", (limit,)
        ).fetchall()
        return [dict(r) for r in rows]

    def get_memories_by_source(self, source: str, limit: int = 50) -> list[dict]:
        """Fetch memories filtered by source."""
        rows = self._conn.execute(
            "SELECT * FROM memories WHERE source = ? ORDER BY id DESC LIMIT ?",
            (source, limit),
        ).fetchall()
        return [dict(r) for r in rows]

    def search_memories(self, keyword: str, limit: int = 50) -> list[dict]:
        """Search memories by keyword in content or tags."""
        rows = self._conn.execute(
            """
            SELECT * FROM memories
            WHERE content LIKE ? OR tags LIKE ?
            ORDER BY id DESC LIMIT ?
            """,
            (f"%{keyword}%", f"%{keyword}%", limit),
        ).fetchall()
        return [dict(r) for r in rows]

    # ==================================================================
    # Queue
    # ==================================================================

    def save_queue(
        self,
        task_type: str,
        payload: str = "",
        priority: int = 0,
    ) -> int:
        """Insert a new pending task. Returns the new row id."""
        cur = self._conn.execute(
            """
            INSERT INTO queue (task_type, payload, status, priority, created_at)
            VALUES (?, ?, 'pending', ?, ?)
            """,
            (task_type, payload, priority, self._now()),
        )
        self._conn.commit()
        return cur.lastrowid

    def get_queue(self, limit: int = 100) -> list[dict]:
        """Fetch all queue tasks, newest first."""
        rows = self._conn.execute(
            "SELECT * FROM queue ORDER BY id DESC LIMIT ?", (limit,)
        ).fetchall()
        return [dict(r) for r in rows]

    def get_next_pending_task(self) -> dict | None:
        """
        Fetch the next pending task (highest priority, then oldest).
        Atomically sets status to 'processing'.
        Returns task dict or None.
        """
        row = self._conn.execute(
            """
            SELECT * FROM queue
            WHERE status = 'pending'
            ORDER BY priority DESC, created_at ASC
            LIMIT 1
            """
        ).fetchone()

        if row is None:
            return None

        task = dict(row)
        now = self._now()
        self._conn.execute(
            "UPDATE queue SET status = 'processing', started_at = ? WHERE id = ?",
            (now, task["id"]),
        )
        self._conn.commit()
        task["status"] = "processing"
        task["started_at"] = now
        return task

    def complete_task(self, task_id: int) -> None:
        """Mark a queue task as completed."""
        self._conn.execute(
            "UPDATE queue SET status = 'completed', completed_at = ? WHERE id = ?",
            (self._now(), task_id),
        )
        self._conn.commit()

    def fail_task(self, task_id: int, error: str = "") -> None:
        """Mark a queue task as failed."""
        self._conn.execute(
            "UPDATE queue SET status = 'failed', completed_at = ?, error = ? WHERE id = ?",
            (self._now(), error, task_id),
        )
        self._conn.commit()

    def get_task(self, task_id: int) -> dict | None:
        """Fetch a single queue task by id."""
        row = self._conn.execute(
            "SELECT * FROM queue WHERE id = ?", (task_id,)
        ).fetchone()
        return dict(row) if row else None

    def reset_task_to_pending(self, task_id: int, retry_count: int) -> None:
        """Reset a task back to pending with updated retry count."""
        self._conn.execute(
            """
            UPDATE queue
            SET status = 'pending', started_at = NULL, completed_at = NULL,
                error = NULL, retry_count = ?
            WHERE id = ?
            """,
            (retry_count, task_id),
        )
        self._conn.commit()

    def get_queue_by_status(self, status: str, limit: int = 50) -> list[dict]:
        """Fetch queue tasks filtered by status."""
        rows = self._conn.execute(
            "SELECT * FROM queue WHERE status = ? ORDER BY id DESC LIMIT ?",
            (status, limit),
        ).fetchall()
        return [dict(r) for r in rows]

    def count_queue_by_status(self) -> dict:
        """Returns {status: count} for all queue tasks."""
        rows = self._conn.execute(
            "SELECT status, COUNT(*) as cnt FROM queue GROUP BY status"
        ).fetchall()
        return {row["status"]: row["cnt"] for row in rows}

    def pending_task_count(self) -> int:
        """Number of pending queue tasks."""
        return self._conn.execute(
            "SELECT COUNT(*) FROM queue WHERE status = 'pending'"
        ).fetchone()[0]

    # ==================================================================
    # Wi-Fi Networks
    # ==================================================================

    def save_wifi_network(self, ssid: str, password: str, priority: int = 0) -> None:
        """Insert or update a saved Wi-Fi network credential."""
        self._conn.execute(
            """
            INSERT INTO wifi_networks (ssid, password, priority, added_at)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(ssid) DO UPDATE SET
                password = excluded.password,
                priority = excluded.priority,
                added_at = excluded.added_at
            """,
            (ssid, password, priority, self._now()),
        )
        self._conn.commit()
        logger.info(f"[DB] Saved Wi-Fi: {ssid} (priority={priority})")

    def get_wifi_networks(self) -> list[dict]:
        """Fetch all saved Wi-Fi network credentials, highest priority (lowest number, starting at 0) first."""
        rows = self._conn.execute(
            "SELECT * FROM wifi_networks ORDER BY priority ASC, added_at DESC"
        ).fetchall()
        return [dict(r) for r in rows]

    def delete_wifi_network(self, ssid: str) -> None:
        """Delete a saved Wi-Fi network credential."""
        self._conn.execute(
            "DELETE FROM wifi_networks WHERE ssid = ?", (ssid,)
        )
        self._conn.commit()
        logger.info(f"[DB] Deleted Wi-Fi: {ssid}")

    # ==================================================================
    # Internal
    # ==================================================================

    def _now(self) -> str:
        """UTC timestamp in ISO format."""
        return datetime.utcnow().isoformat()
