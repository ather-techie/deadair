from fastapi import FastAPI

from deadair.container import Container
from deadair.presentation.api import jobs, videos
from deadair.presentation.api.error_handlers import register_error_handlers


def create_app(container: Container) -> FastAPI:
    app = FastAPI(title="deadair")
    app.state.container = container
    app.include_router(videos.router)
    app.include_router(jobs.router)
    register_error_handlers(app)
    return app
