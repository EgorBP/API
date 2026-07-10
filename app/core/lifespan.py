from contextlib import asynccontextmanager
from app.core.redis import create_redis_client, close_redis_client
from fastapi import FastAPI
import logging

logger = logging.getLogger("app.lifespan")


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.redis = await create_redis_client()
    logger.info("Redis successfully connected.")
    
    yield

    await close_redis_client(app.state.redis)
    logger.info("Redis connection successfully closed.")
