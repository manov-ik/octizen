from fastapi import APIRouter, status
from memory.models import Log, LogCreate
from memory.manager import memory_manager

router = APIRouter(prefix="/api/logs", tags=["logs"])

@router.get("", response_model=list[Log])
def get_logs():
    return memory_manager.get_logs()

@router.post("", response_model=Log, status_code=status.HTTP_201_CREATED)
def create_log(log_in: LogCreate):
    return memory_manager.add_log(log_in)
