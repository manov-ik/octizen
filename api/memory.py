from fastapi import APIRouter, HTTPException, status
from memory.models import Memory, MemoryCreate
from memory.manager import memory_manager

router = APIRouter(prefix="/api/memories", tags=["memories"])

@router.get("", response_model=list[Memory])
def get_memories():
    return memory_manager.get_memories()

@router.post("", response_model=Memory, status_code=status.HTTP_201_CREATED)
def create_memory(memory_in: MemoryCreate):
    return memory_manager.add_memory(memory_in)

@router.delete("/{memory_id}")
def delete_memory(memory_id: int):
    success = memory_manager.delete_memory(memory_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Memory with ID {memory_id} not found"
        )
    return {"success": True, "message": f"Memory {memory_id} successfully deleted"}
