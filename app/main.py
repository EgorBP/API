from fastapi import FastAPI
from fastapi.params import Depends
from app.routers import user, search
from app.core.lifespan import lifespan
from app.core.dependencies import verify_secret_key
from app.core.logging.config import setup_logging
from app.core.exceptions import AppExceptionHandlers
from app.middleware.request_logging import ASGIRequestLoggingMiddleware


setup_logging()

app = FastAPI(
    lifespan=lifespan,
    dependencies=[Depends(verify_secret_key)]
)

AppExceptionHandlers().register(app)
app.add_middleware(ASGIRequestLoggingMiddleware)

app.include_router(search.router)
app.include_router(user.router)
