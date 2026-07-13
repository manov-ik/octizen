"""
api/routes/health.py

Health check endpoint. Returns uptime and connection status of core managers.
"""

import time
from fastapi import APIRouter, Request

router = APIRouter(prefix="/health", tags=["Health"])


@router.get("")
def get_health(request: Request):
    db = request.app.state.db

    # Database connectivity check
    try:
        db.get_logs(limit=1)
        db_status = "connected"
    except Exception:
        db_status = "disconnected"

    uptime_sec = time.time() - getattr(request.app.state, "start_time", time.time())

    return {
        "status": "healthy",
        "database": db_status,
        "queue": "running",
        "uptime": f"{uptime_sec:.1f}s",
    }
