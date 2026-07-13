"""
api/routes/notes.py

Notes endpoint. Allows reading and creating text notes.
"""

from fastapi import APIRouter, Request
from api.schemas import NoteCreate

router = APIRouter(prefix="/notes", tags=["Notes"])


@router.get("")
def read_notes(request: Request, limit: int = 100):
    db = request.app.state.db
    return db.get_notes(limit=limit)


@router.post("")
def create_note(request: Request, note: NoteCreate):
    db = request.app.state.db
    note_id = db.save_note(note.title, note.content)
    return {"id": note_id, "title": note.title, "status": "saved"}
