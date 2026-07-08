from contextlib import asynccontextmanager
from app.core.redis import create_redis_client, close_redis_client
from fastapi import FastAPI


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.redis = await create_redis_client()
    
    yield

    await close_redis_client(app.state.redis)
