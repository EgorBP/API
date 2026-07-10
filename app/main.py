from fastapi import FastAPI
from fastapi.params import Depends
from app.routers import user, search
from app.core.lifespan import lifespan
from app.core.dependencies import verify_secret_key
from app.core.log_config import setup_logging


setup_logging()

app = FastAPI(
    lifespan=lifespan,
    dependencies=[Depends(verify_secret_key)]
)

app.include_router(search.router)
app.include_router(user.router)
