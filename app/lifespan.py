from contextlib import asynccontextmanager
import redis.asyncio as redis
from fastapi import FastAPI


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.redis = redis.Redis(
        host="redis",
        port=6379,
        decode_responses=True
    )

    yield

    await app.state.redis.close()
