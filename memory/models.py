from pydantic import BaseModel
from typing import Optional

class MemoryBase(BaseModel):
    title: str
    content: str
    type: str = "idea"
    source: str = "manual"

class MemoryCreate(MemoryBase):
    pass

class Memory(MemoryBase):
    id: int
    created_at: str
    updated_at: str
    favorite: int

class LogBase(BaseModel):
    message: str
    level: str = "INFO"

class LogCreate(LogBase):
    pass

class Log(LogBase):
    id: int
    created_at: str
