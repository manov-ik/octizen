"""
core/app.py

Main Octizen application class.
Bootstraps storage, GPIO, and all services in the correct order.
"""

from core.logger import logger
from core.config import Config
from storage import Database, EventRepo, LogRepo, SettingRepo, NotificationRepo


class Octizen:
    def __init__(self):
        self.config = Config()
        self.db = Database()

        # Repositories — available to all services after start()
        self.events: EventRepo | None = None
        self.logs: LogRepo | None = None
        self.settings: SettingRepo | None = None
        self.notifications: NotificationRepo | None = None

    def start(self):
        logger.info("Starting Octizen...")
        logger.info(f"Version: {self.config.VERSION}")

        # ── 1. Storage ────────────────────────────────────────────────
        self.db.init_db()
        self.events       = EventRepo(self.db)
        self.logs         = LogRepo(self.db)
        self.settings     = SettingRepo(self.db)
        self.notifications = NotificationRepo(self.db)
        logger.info("Storage layer ready.")

        # ── 2. GPIO / Button ──────────────────────────────────────────
        from devices.button import ButtonManager
        self.button = ButtonManager(on_press=self._on_button_press)
        self.button.start()   # blocks here — listens forever

        # ── 3. Future: Logger service, Event bus, Dashboard, Voice ─────

        logger.info("Octizen is ready ✅")

    def stop(self):
        """Clean shutdown — flush DB, release GPIO, etc."""
        logger.info("Shutting down Octizen...")
        self.db.close()
        logger.info("Goodbye.")

    # ------------------------------------------------------------------
    # Callbacks (wired up as services are added)
    # ------------------------------------------------------------------

    def _on_button_press(self, pin: int):
        """Called by ButtonManager on every button press."""
        if self.events:
            event_id = self.events.insert(
                pin=pin,
                event_type="button_pressed",
                source="gpio",
            )
            logger.info(f"[Event] button_pressed on pin {pin} → id={event_id}")
