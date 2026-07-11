import os
import sqlite3
from datetime import datetime, timedelta, timezone
from contextlib import contextmanager
from core.logger import logger

class Database:
    def __init__(self, db_path: str = "storage/octizen.db"):
        self.db_path = db_path
        # Ensure database directory exists
        db_dir = os.path.dirname(self.db_path)
        if db_dir:
            os.makedirs(db_dir, exist_ok=True)

    @contextmanager
    def get_connection(self):
        # check_same_thread=False is required because gpiozero's when_pressed
        # callback fires on a background thread. Without this, any SQLite write
        # from the physical button press raises a threading error and is silently
        # lost — which is why button presses were not appearing on the dashboard.
        conn = sqlite3.connect(self.db_path, check_same_thread=False)
        # Enable dictionary-like access to rows
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        except Exception as e:
            conn.rollback()
            logger.error(f"Database error: {e}")
            raise e
        finally:
            conn.close()

    def init_db(self):
        logger.info("Initializing database...")
        
        with self.get_connection() as conn:
            # Create memories table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS memories (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    content TEXT NOT NULL,
                    type TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    source TEXT NOT NULL,
                    favorite INTEGER DEFAULT 0
                )
            """)
            
            # Create logs table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    message TEXT NOT NULL,
                    level TEXT NOT NULL,
                    created_at TEXT NOT NULL
                )
            """)
            
            # Check if seeding is needed (first run only - no memories present)
            cursor = conn.execute("SELECT COUNT(*) FROM memories")
            count = cursor.fetchone()[0]
            if count == 0:
                self._seed_dummy_data(conn)

    def _seed_dummy_data(self, conn):
        logger.info("First run detected. Seeding dummy data...")
        
        now = datetime.now(timezone.utc)
        
        # 10 dummy memories
        dummy_memories = [
            ("Project Kickoff", "Successfully cloned and initialized the Octizen workspace for Sprint 1.", "log", "system", 10),
            ("Idea: Ambient Sound Engine", "Consider integrating localized white noise and relaxing binaural beats in Sprint 2.", "idea", "manual", 9),
            ("Feature request: Dark Mode toggle", "Allow users to swap between Deep Space and Cyberpunk neon dashboards.", "idea", "user", 8),
            ("Bug: Fix Memory Ordering", "API output needs to sort memories strictly newest first by created_at.", "bug", "system", 7),
            ("AI Memory Consolidation Study", "Review papers on semantic vector embeddings for memory consolidation loops.", "idea", "manual", 6),
            ("SQLite DB Created", "Auto-created storage/octizen.db structure with table validation.", "log", "system", 5),
            ("User Feedback on UI", "The glassmorphic dashboard design is extremely responsive and fits nicely.", "idea", "user", 4),
            ("REST API Endpoints Documented", "Verified all API operations map correctly to memory manager routes.", "log", "system", 3),
            ("Manual Testing Sandbox", "Adding a manual memory card to test frontend list rendering dynamics.", "idea", "manual", 2),
            ("Sprint 1 Complete", "Code finalized for SQLite creation, memory seeding, and 1-second auto refresh dashboard.", "idea", "manual", 1)
        ]
        
        for title, content, m_type, source, offset_hours in dummy_memories:
            timestamp = (now - timedelta(hours=offset_hours)).strftime("%Y-%m-%dT%H:%M:%SZ")
            conn.execute(
                """
                INSERT INTO memories (title, content, type, created_at, updated_at, source, favorite)
                VALUES (?, ?, ?, ?, ?, ?, 0)
                """,
                (title, content, m_type, timestamp, timestamp, source)
            )

        # 20 dummy logs
        dummy_log_templates = [
            ("Octizen application boot sequence started", "INFO", 20),
            ("Loading core configuration...", "DEBUG", 19),
            ("Database file checked at storage/octizen.db", "DEBUG", 18),
            ("Database schema verification passed", "INFO", 17),
            ("Initializing table: memories", "DEBUG", 16),
            ("Initializing table: logs", "DEBUG", 15),
            ("First run check: No existing records found", "INFO", 14),
            ("Seeding 10 dummy memories", "INFO", 13),
            ("Seeding 20 dummy logs", "INFO", 12),
            ("FastAPI application instance created", "INFO", 11),
            ("Registered router: /api/memories", "DEBUG", 10),
            ("Registered router: /api/logs", "DEBUG", 9),
            ("Mounted static dashboard resources under /static", "DEBUG", 8),
            ("Uvicorn listening on http://0.0.0.0:8000", "INFO", 7),
            ("Server running under development reload mode", "WARNING", 6),
            ("Dashboard accessed from user client at /", "INFO", 5),
            ("API GET /api/memories requested by client", "DEBUG", 4),
            ("API GET /api/logs requested by client", "DEBUG", 3),
            ("Query returned 10 memories and 20 logs", "INFO", 2),
            ("System health check OK: Memory usage 42%", "INFO", 1)
        ]

        for message, level, offset_minutes in dummy_log_templates:
            timestamp = (now - timedelta(minutes=offset_minutes)).strftime("%Y-%m-%dT%H:%M:%SZ")
            conn.execute(
                """
                INSERT INTO logs (message, level, created_at)
                VALUES (?, ?, ?)
                """,
                (message, level, timestamp)
            )

        logger.info("Dummy data seeding complete.")

    def fetch_all_memories(self):
        with self.get_connection() as conn:
            cursor = conn.execute("SELECT * FROM memories ORDER BY created_at DESC, id DESC")
            return [dict(row) for row in cursor.fetchall()]

    def insert_memory(self, title: str, content: str, m_type: str, source: str, created_at: str, updated_at: str, favorite: int = 0):
        with self.get_connection() as conn:
            cursor = conn.execute(
                """
                INSERT INTO memories (title, content, type, source, created_at, updated_at, favorite)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (title, content, m_type, source, created_at, updated_at, favorite)
            )
            inserted_id = cursor.lastrowid
            # Retrieve the full inserted row
            row = conn.execute("SELECT * FROM memories WHERE id = ?", (inserted_id,)).fetchone()
            return dict(row)

    def delete_memory(self, memory_id: int) -> bool:
        with self.get_connection() as conn:
            # Check if it exists
            row = conn.execute("SELECT id FROM memories WHERE id = ?", (memory_id,)).fetchone()
            if not row:
                return False
            conn.execute("DELETE FROM memories WHERE id = ?", (memory_id,))
            return True

    def fetch_all_logs(self):
        with self.get_connection() as conn:
            cursor = conn.execute("SELECT * FROM logs ORDER BY created_at DESC, id DESC")
            return [dict(row) for row in cursor.fetchall()]

    def insert_log(self, message: str, level: str, created_at: str):
        with self.get_connection() as conn:
            cursor = conn.execute(
                """
                INSERT INTO logs (message, level, created_at)
                VALUES (?, ?, ?)
                """,
                (message, level, created_at)
            )
            inserted_id = cursor.lastrowid
            row = conn.execute("SELECT * FROM logs WHERE id = ?", (inserted_id,)).fetchone()
            return dict(row)

# Shared global instance
db = Database()
