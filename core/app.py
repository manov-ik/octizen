"""
core/app.py

Main Octizen application class.
Pure wiring — connects storage, event middleware, and device managers.
"""

from core.logger import logger
from core.config import Config
from core.event_manager import EventManager
from storage import Database


class Octizen:
    def __init__(self):
        self.config = Config()

    def start(self):
        logger.info("Starting Octizen...")
        logger.info(f"Version: {self.config.VERSION}")

        # ── 1. Storage ────────────────────────────────────────────────
        self.db = Database()
        self.db.init_db()

        # ── 2. Event middleware ───────────────────────────────────────
        self.event_manager = EventManager(self.db)

        # ── 3. Button (blocks forever via pause()) ────────────────────
        from devices.button import ButtonManager
        self.button = ButtonManager(self.event_manager)
        self.button.start()

    def stop(self):
        """Clean shutdown."""
        logger.info("Shutting down Octizen...")
        self.db.close()
        logger.info("Goodbye.")
