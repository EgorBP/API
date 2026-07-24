import asyncio
from contextlib import asynccontextmanager
from app.core.redis import create_redis_client, close_redis_client
from fastapi import FastAPI
import logging

from app.tasks.gif import recalculate_popular_gifs_loop
from app.tasks.tag import recalculate_popular_tags_loop

logger = logging.getLogger("app.lifespan")


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.redis = await create_redis_client()
    logger.info("Redis successfully connected.")

    gifs_task = asyncio.create_task(
        recalculate_popular_gifs_loop(
            redis=app.state.redis,
            recalc_after=300,
            limit=100
        )
    )
    tags_task = asyncio.create_task(
        recalculate_popular_tags_loop(
            redis=app.state.redis,
            recalc_after=300,
            limit=100
        )
    )
    logger.info("Background tasks successfully started")
    
    yield

    gifs_task.cancel()
    tags_task.cancel()
    await asyncio.gather(gifs_task, tags_task, return_exceptions=True)
    logger.info("All background tasks successfully canceled.")

    await close_redis_client(app.state.redis)
    logger.info("Redis connection successfully closed.")
