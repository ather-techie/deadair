from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from deadair.container import Container
from deadair.presentation.api import jobs, system, videos
from deadair.presentation.api.error_handlers import register_error_handlers

CLIENT_DIR = Path(__file__).resolve().parents[5] / "client"


def create_app(container: Container) -> FastAPI:
    app = FastAPI(title="deadair")
    app.state.container = container
    app.include_router(videos.router)
    app.include_router(jobs.router)
    app.include_router(system.router)
    register_error_handlers(app)
    if CLIENT_DIR.is_dir():
        app.mount("/", StaticFiles(directory=CLIENT_DIR, html=True), name="client")
    return app
