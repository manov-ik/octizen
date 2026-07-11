import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from storage.database import db
from api.memory import router as memory_router
from api.logs import router as logs_router
from memory.manager import memory_manager
from devices.button import setup_button, trigger_press

@asynccontextmanager
async def lifespan(app: FastAPI):
    db.init_db()
    setup_button(memory_manager)
    yield

app = FastAPI(
    title="Octizen Memory Engine",
    description="Sprint 1 - Memory Engine v0.1",
    lifespan=lifespan
)

# Register routers
app.include_router(memory_router)
app.include_router(logs_router)

# Mount dashboard directory for static files (CSS, JS)
# Ensure the dashboard directory exists to avoid startup error
os.makedirs("dashboard", exist_ok=True)
app.mount("/static", StaticFiles(directory="dashboard"), name="static")

@app.get("/")
def read_root():
    return FileResponse(os.path.join("dashboard", "index.html"))

@app.get("/style.css")
def read_style():
    return FileResponse(os.path.join("dashboard", "style.css"))

@app.get("/script.js")
def read_script():
    return FileResponse(os.path.join("dashboard", "script.js"))

@app.post("/api/button-press")
def manual_button_press():
    """Simulate a physical button press via the API.
    Enqueues through the same worker thread as the real GPIO event.
    Use this to verify the data flow without touching the hardware:
      curl -X POST http://localhost:8000/api/button-press
    """
    trigger_press()
    return {"success": True, "message": "Button press event queued — check the dashboard."}
