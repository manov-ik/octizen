"""
storage/models.py

Dataclass definitions for all database table schemas.
These map 1-to-1 with SQLite tables.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


@dataclass
class Event:
    """
    Represents a hardware or software event (e.g. GPIO button press).
    """
    id: Optional[int] = None
    pin: int = 0
    event_type: str = ""          # e.g. "button_pressed", "button_released"
    source: str = ""              # e.g. "gpio", "system"
    notes: str = ""
    timestamp: str = field(
        default_factory=lambda: datetime.utcnow().isoformat()
    )


@dataclass
class Log:
    """
    Represents a single system log entry.
    """
    id: Optional[int] = None
    level: str = "INFO"           # DEBUG | INFO | WARNING | ERROR | CRITICAL
    message: str = ""
    source: str = ""              # module/component that generated the log
    timestamp: str = field(
        default_factory=lambda: datetime.utcnow().isoformat()
    )


@dataclass
class Setting:
    """
    Key/value persistent configuration store.
    """
    key: str = ""
    value: str = ""
    description: str = ""
    updated_at: str = field(
        default_factory=lambda: datetime.utcnow().isoformat()
    )


@dataclass
class Notification:
    """
    Represents a notification that was sent or queued.
    """
    id: Optional[int] = None
    title: str = ""
    body: str = ""
    channel: str = "system"       # e.g. "system", "push", "email"
    status: str = "pending"       # pending | sent | failed
    timestamp: str = field(
        default_factory=lambda: datetime.utcnow().isoformat()
    )
