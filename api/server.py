import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from storage.database import db
from api.memory import router as memory_router
from api.logs import router as logs_router
from memory.manager import memory_manager
from devices.button import setup_button

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize database tables and seed dummy data on app startup
    db.init_db()
    # Setup physical button listener on GPIO17
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
