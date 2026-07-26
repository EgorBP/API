"""FastAPI application entry point.

Wires together logging, the app-level exception handlers, the request
logging middleware, the API router, and the startup/shutdown lifespan
(Redis connection + background popularity-recalculation tasks). Run via
Uvicorn/Gunicorn as configured in the Dockerfile.
"""

from fastapi import FastAPI

from app.api import api_router
from app.api.exception_handlers import AppExceptionHandlers
from app.api.middleware import ASGIRequestLoggingMiddleware
from app.core.lifespan import lifespan
from app.core.logging.config import setup_logging

setup_logging()

app = FastAPI(
    title="GIFs API",
    version="1.0.0",
    lifespan=lifespan,
)

AppExceptionHandlers().register(app)
app.add_middleware(ASGIRequestLoggingMiddleware)

app.include_router(api_router)
