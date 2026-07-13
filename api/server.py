"""
api/server.py

FastAPI server entry point.
Exposes REST routers and launches uvicorn loop.
"""

import uvicorn
from fastapi import FastAPI
from api.routes import health, logs, notes, memories, queue


def create_app(octizen_app) -> FastAPI:
    """Builds FastAPI application with state context dependency injection."""
    app = FastAPI(title="Octizen Local API", version="0.1.0")

    # Store shared references in app.state for DI in routes
    app.state.db = octizen_app.db
    app.state.queue = octizen_app.queue
    app.state.start_time = octizen_app.start_time
    app.state.config = octizen_app.config

    @app.get("/")
    def index():
        return {"status": "running", "version": octizen_app.config.VERSION}

    # Register routers
    app.include_router(health.router)
    app.include_router(logs.router)
    app.include_router(notes.router)
    app.include_router(memories.router)
    app.include_router(queue.router)

    return app


def start_api_server(octizen_app):
    """Launches uvicorn blocking web server thread."""
    app = create_app(octizen_app)
    host = octizen_app.config.HOST
    port = octizen_app.config.PORT
    uvicorn.run(app, host=host, port=port, log_level="info")
