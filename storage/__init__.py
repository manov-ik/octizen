"""
storage/__init__.py

Clean public API for the storage module.

Usage:
    from storage import Database, EventRepo, LogRepo, SettingRepo, NotificationRepo
"""

from storage.database import Database
from storage.repository import EventRepo, LogRepo, SettingRepo, NotificationRepo
from storage.models import Event, Log, Setting, Notification

__all__ = [
    "Database",
    "EventRepo",
    "LogRepo",
    "SettingRepo",
    "NotificationRepo",
    "Event",
    "Log",
    "Setting",
    "Notification",
]
