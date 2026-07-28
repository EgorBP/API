import asyncio
import logging

from redis.asyncio import Redis

from app.core.database import AsyncSessionLocal
from app.repositories import TagRepository
from app.schemas.tag import PopularTagsOut

logger = logging.getLogger(__name__)


async def recalculate_popular_tags_loop(
        redis: Redis,
        limit: int,
        recalc_after: int
):
    """Periodically recomputes and caches the site-wide popular tags list.

    Runs forever until cancelled: computes the popular tags, stores them
    in Redis under `"popular:tags"`, sleeps for `recalc_after` seconds,
    and repeats. A failure on one iteration is logged and does not stop
    the loop — the stale cached value is simply left in place until the
    next successful iteration.

    Meant to be launched as a background task from `app.core.lifespan`
    and canceled on application shutdown.

    Args:
        redis: The Redis client to write the cached result to.
        limit: Maximum number of tags to include in the popular list.
        recalc_after: Delay between recalculations, in seconds.

    Raises:
        asyncio.CancelledError: Propagated when the task is canceled,
            so the caller can await its clean shutdown.
    """
    while True:
        try:
            async with AsyncSessionLocal() as session:
                tag_repo = TagRepository(session)

                popular_tags = await tag_repo.get_popular_tags(limit)

                popular_gifs_out = PopularTagsOut(
                    tags=popular_tags,
                    count=len(popular_tags)
                )

                await redis.set("popular:tags", popular_gifs_out.model_dump_json())
                logger.info("Popular tags updated")
        except asyncio.CancelledError:
            logger.debug("Stopping popular tags updating task...")
            raise 
        except Exception:
            logger.exception("Error when update popular tags")

        await asyncio.sleep(recalc_after)
