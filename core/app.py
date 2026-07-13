"""
core/app.py

Main Octizen application class.
Pure wiring — connects storage, event middleware, and device managers.
"""

import time
from core.logger import logger
from core.config import Config
from core.event_manager import EventManager
from core.queue_manager import QueueManager
from storage import DatabaseManager


class Octizen:
    def __init__(self):
        self.config = Config()
        self.start_time = 0.0

    def start(self):
        self.start_time = time.time()
        logger.info("Starting Octizen...")
        logger.info(f"Version: {self.config.VERSION}")

        # ── 1. Storage ────────────────────────────────────────────────
        self.db = DatabaseManager()
        self.db.init_db()

        # ── 2. Event middleware ───────────────────────────────────────
        self.event_manager = EventManager(self.db)

        # ── 3. Queue ──────────────────────────────────────────────────
        self.queue = QueueManager(self.db, self.event_manager)

        # ── 4. Button (non-blocking initialization) ───────────────────
        from devices.button import ButtonManager
        self.button = ButtonManager(self.event_manager)
        self.button.start()

        # ── 5. FastAPI Web Server (blocking) ──────────────────────────
        from api.server import start_api_server
        start_api_server(self)

    def stop(self):
        """Clean shutdown."""
        logger.info("Shutting down Octizen...")
        self.db.close()
        logger.info("Goodbye.")
