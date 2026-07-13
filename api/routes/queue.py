"""
api/routes/queue.py

Queue checker endpoint. Returns pending tasks.
"""

from fastapi import APIRouter, Request

router = APIRouter(prefix="/queue", tags=["Queue"])


@router.get("")
def read_pending_queue(request: Request, limit: int = 100):
    queue = request.app.state.queue
    return queue.get_by_status("pending", limit=limit)
