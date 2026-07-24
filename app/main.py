from fastapi import FastAPI
from app.api import api_router
from app.core.lifespan import lifespan
from app.core.logging.config import setup_logging
from app.api.exception_handlers import AppExceptionHandlers
from app.api.middleware import ASGIRequestLoggingMiddleware


setup_logging()

app = FastAPI(
    title="GIFs API",
    version="1.0.0",
    lifespan=lifespan,
)

AppExceptionHandlers().register(app)
app.add_middleware(ASGIRequestLoggingMiddleware)

app.include_router(api_router)

# TODO:
"""
докстринги
тесты
"""
