"""FastAPI application entry point."""
import time

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.routes import router
from app.config import get_settings
from app.exceptions import (
    ConfigError,
    EmptyDocumentError,
    ExternalServiceError,
    FileTooLargeError,
    UnsupportedFileError,
)
from app.logger import get_logger, setup_logging

setup_logging(get_settings().log_level)
logger = get_logger(__name__)

app = FastAPI(
    title="Medical RAG Assistant",
    version="1.0.0",
    description="Answers medical questions from uploaded documents, with source references.",
)
# Restrict allow_origins to your Streamlit URL in production.
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

_STATUS_CODES = {
    ConfigError: 503,
    UnsupportedFileError: 400,
    FileTooLargeError: 413,
    EmptyDocumentError: 422,
    ExternalServiceError: 503,
}


def _make_handler(status_code: int):
    async def handler(request: Request, exc: Exception):
        logger.error("%s on %s: %s", type(exc).__name__, request.url.path, exc)
        return JSONResponse(status_code=status_code, content={"detail": str(exc)})

    return handler


for _exc_class, _code in _STATUS_CODES.items():
    app.add_exception_handler(_exc_class, _make_handler(_code))


@app.middleware("http")
async def log_requests(request: Request, call_next):
    start = time.perf_counter()
    response = await call_next(request)
    logger.info(
        "%s %s -> %d (%.0f ms)",
        request.method, request.url.path, response.status_code,
        (time.perf_counter() - start) * 1000,
    )
    return response


app.include_router(router)
