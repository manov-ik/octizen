"""
api/routes/memories.py

Memories endpoint. Allows reading and creating memories.
"""

from fastapi import APIRouter, Request
from api.schemas import MemoryCreate

router = APIRouter(prefix="/memories", tags=["Memories"])


@router.get("")
def read_memories(request: Request, limit: int = 100):
    db = request.app.state.db
    return db.get_memories(limit=limit)


@router.post("")
def create_memory(request: Request, memory: MemoryCreate):
    db = request.app.state.db
    memory_id = db.save_memory(memory.content, memory.source, memory.tags)
    return {"id": memory_id, "content": memory.content, "status": "saved"}
