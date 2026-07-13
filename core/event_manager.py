"""
core/event_manager.py

Central event bus for Octizen.
Every action in the system flows through EventManager.emit().

Responsibilities:
    1. Log every event to SQLite (via Database.log_event)
    2. Print every event to terminal
    3. Notify registered listeners (for future sprints)

Usage:
    em = EventManager(db)
    em.emit("button.pressed", {"pin": 17, "name": "main"})
"""

from core.logger import logger
from storage.database import Database


class EventManager:
    """
    Middleware between hardware managers and storage.
    Single entry point for all system events.
    """

    def __init__(self, db: Database):
        self._db = db
        self._listeners: dict[str, list] = {}

    def on(self, event_name: str, callback) -> None:
        """
        Register a listener for an event type.

        Args:
            event_name: e.g. "button.pressed"
            callback:   fn(event_name: str, data: dict)
        """
        self._listeners.setdefault(event_name, []).append(callback)

    def emit(self, event_name: str, data: dict | None = None) -> int:
        """
        Emit an event. This is the ONLY way events enter the system.

        1. Print to terminal
        2. Write to SQLite logs table
        3. Call any registered listeners

        Args:
            event_name: e.g. "button.pressed"
            data:       optional context dict, e.g. {"pin": 17, "name": "main"}

        Returns:
            The log row id from SQLite.
        """
        data = data or {}

        # 1. Terminal
        logger.info(f"[Event] {event_name}  {data}")

        # Format details into the event string so they are saved in SQLite
        db_event = event_name
        if data:
            # e.g., "button.pressed: main (pin 17)"
            details = ", ".join(f"{k}={v}" for k, v in data.items())
            db_event = f"{event_name} ({details})"

        # 2. Persist
        row_id = self._db.log_event(db_event)

        # 3. Listeners
        for cb in self._listeners.get(event_name, []):
            try:
                cb(event_name, data)
            except Exception as e:
                logger.error(f"[Event] Listener error for {event_name}: {e}")

        return row_id
