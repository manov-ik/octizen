"""
api/routes/logs.py

Logs check endpoint. Returns historical system events.
"""

from fastapi import APIRouter, Request

router = APIRouter(prefix="/logs", tags=["Logs"])


@router.get("")
def read_logs(request: Request, limit: int = 100):
    db = request.app.state.db
    return db.get_logs(limit=limit)
