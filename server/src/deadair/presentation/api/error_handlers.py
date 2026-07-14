import logging

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from deadair.application.ports.job_repository import JobAlreadyExistsError, JobNotFoundError

logger = logging.getLogger(__name__)


def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(JobNotFoundError)
    async def _job_not_found(request: Request, exc: JobNotFoundError) -> JSONResponse:
        return JSONResponse(status_code=404, content={"detail": str(exc)})

    @app.exception_handler(JobAlreadyExistsError)
    async def _job_already_exists(request: Request, exc: JobAlreadyExistsError) -> JSONResponse:
        return JSONResponse(status_code=409, content={"detail": str(exc)})

    @app.exception_handler(Exception)
    async def _unhandled(request: Request, exc: Exception) -> JSONResponse:
        logger.exception("unhandled error handling %s %s", request.method, request.url)
        return JSONResponse(status_code=500, content={"detail": "internal server error"})
