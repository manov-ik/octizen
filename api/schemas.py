"""
api/schemas.py

Pydantic schemas for request validation.
"""

from pydantic import BaseModel


class NoteCreate(BaseModel):
    title: str
    content: str = ""


class MemoryCreate(BaseModel):
    content: str
    source: str = "api"
    tags: str = ""


class WifiSave(BaseModel):
    ssid: str
    password: str
    priority: int = 0
