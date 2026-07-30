import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.core.redis import close_redis_client, create_redis_client
from app.tasks.gif import recalculate_popular_gifs_loop
from app.tasks.tag import recalculate_popular_tags_loop

logger = logging.getLogger("app.lifespan")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manages startup and shutdown of shared application resources.

    On startup, connects to Redis and launches the background tasks that
    periodically recalculate popular GIFs and tags. On shutdown, cancels
    those tasks and closes the Redis connection, in that order.

    Args:
        app: The FastAPI application instance. The created Redis client is
            stored on `app.state.redis`.

    Yields:
        None. Control returns to FastAPI while the application serves
        requests; teardown runs after the `yield` resumes.
    """
    app.state.redis = await create_redis_client()
    logger.info("Redis successfully connected.")

    gifs_task = asyncio.create_task(
        recalculate_popular_gifs_loop(
            redis=app.state.redis,
            # recalc_after=300,
            recalc_after=30,
            limit=100
        )
    )
    tags_task = asyncio.create_task(
        recalculate_popular_tags_loop(
            redis=app.state.redis,
            # recalc_after=300,
            recalc_after=30,
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
