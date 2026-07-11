"""
storage/database.py

Core Database class for Octizen.
Handles SQLite connection lifecycle, schema creation, and migrations.

Usage:
    db = Database()
    db.init_db()          # Creates tables if they don't exist
    conn = db.get_conn()  # Get raw connection for queries
    db.close()            # Clean shutdown
"""

import sqlite3
import os
from pathlib import Path
from core.logger import logger


# Default path: project root / data / octizen.db
DB_DIR = Path(__file__).resolve().parent.parent / "data"
DB_PATH = DB_DIR / "octizen.db"


class Database:
    """
    Manages the SQLite database connection and schema for Octizen.
    """

    def __init__(self, db_path: str | Path = DB_PATH):
        self.db_path = Path(db_path)
        self._conn: sqlite3.Connection | None = None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def init_db(self) -> None:
        """
        Opens the database connection and ensures all tables exist.
        Call this once at application startup.
        """
        self._ensure_data_dir()
        self._conn = sqlite3.connect(
            str(self.db_path),
            check_same_thread=False,   # safe for single-threaded use
            detect_types=sqlite3.PARSE_DECLTYPES,
        )
        self._conn.row_factory = sqlite3.Row   # dicts instead of tuples
        self._conn.execute("PRAGMA journal_mode=WAL;")  # better concurrency
        self._conn.execute("PRAGMA foreign_keys=ON;")
        self._create_tables()
        self._seed_defaults()
        logger.info(f"[DB] Connected → {self.db_path}")

    def get_conn(self) -> sqlite3.Connection:
        """Returns the active connection. Raises if not initialised."""
        if self._conn is None:
            raise RuntimeError(
                "Database not initialised. Call init_db() first."
            )
        return self._conn

    def close(self) -> None:
        """Commits any pending writes and closes the connection."""
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
        sql = """
        -- ── Events ──────────────────────────────────────────────────
        CREATE TABLE IF NOT EXISTS events (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            pin         INTEGER NOT NULL DEFAULT 0,
            event_type  TEXT    NOT NULL DEFAULT '',
            source      TEXT    NOT NULL DEFAULT '',
            notes       TEXT             DEFAULT '',
            timestamp   TEXT    NOT NULL DEFAULT (datetime('now'))
        );

        -- ── Logs ─────────────────────────────────────────────────────
        CREATE TABLE IF NOT EXISTS logs (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            level       TEXT    NOT NULL DEFAULT 'INFO',
            message     TEXT    NOT NULL DEFAULT '',
            source      TEXT             DEFAULT '',
            timestamp   TEXT    NOT NULL DEFAULT (datetime('now'))
        );

        -- ── Settings ─────────────────────────────────────────────────
        CREATE TABLE IF NOT EXISTS settings (
            key         TEXT    PRIMARY KEY,
            value       TEXT    NOT NULL DEFAULT '',
            description TEXT             DEFAULT '',
            updated_at  TEXT    NOT NULL DEFAULT (datetime('now'))
        );

        -- ── Notifications ─────────────────────────────────────────────
        CREATE TABLE IF NOT EXISTS notifications (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            title       TEXT    NOT NULL DEFAULT '',
            body        TEXT             DEFAULT '',
            channel     TEXT    NOT NULL DEFAULT 'system',
            status      TEXT    NOT NULL DEFAULT 'pending',
            timestamp   TEXT    NOT NULL DEFAULT (datetime('now'))
        );
        """
        conn = self.get_conn()
        conn.executescript(sql)
        conn.commit()
        logger.info("[DB] Tables verified / created.")

    # ------------------------------------------------------------------
    # Seed defaults
    # ------------------------------------------------------------------

    def _seed_defaults(self) -> None:
        """
        Inserts default settings rows on first run.
        Uses INSERT OR IGNORE so it never overwrites existing values.
        """
        defaults = [
            ("app.name",    "Octizen",  "Application display name"),
            ("app.version", "0.1.0",    "Current version"),
            ("button.pin",  "17",       "GPIO pin for the main button (BCM)"),
            ("button.bounce_time", "0.2", "Debounce time in seconds"),
            ("log.level",   "INFO",     "Minimum log level to persist"),
        ]
        conn = self.get_conn()
        conn.executemany(
            """
            INSERT OR IGNORE INTO settings (key, value, description)
            VALUES (?, ?, ?)
            """,
            defaults,
        )
        conn.commit()
        logger.info("[DB] Default settings seeded.")

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _ensure_data_dir(self) -> None:
        """Creates the data directory if it does not exist."""
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
