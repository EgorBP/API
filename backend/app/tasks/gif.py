import asyncio
import logging

from redis.asyncio import Redis

from app.core.database import AsyncSessionLocal
from app.repositories import GifRepository
from app.schemas.gif import PopularGifsOut, RawGifOut

logger = logging.getLogger(__name__)


async def recalculate_popular_gifs_loop(
        redis: Redis,
        limit: int,
        recalc_after: int
):
    """Periodically recomputes and caches the site-wide popular GIFs list.

    Runs forever until cancelled: computes the popular GIFs, stores them
    in Redis under `"popular:gifs"`, sleeps for `recalc_after` seconds,
    and repeats. A failure on one iteration (e.g. a transient database
    error) is logged and does not stop the loop — the stale cached value
    is simply left in place until the next successful iteration.

    Meant to be launched as a background task from `app.core.lifespan`
    and canceled on application shutdown.

    Args:
        redis: The Redis client to write the cached result to.
        limit: Maximum number of GIFs to include in the popular list.
        recalc_after: Delay between recalculations, in seconds.

    Raises:
        asyncio.CancelledError: Propagated when the task is canceled,
            so the caller can await its clean shutdown.
    """
    while True:
        try:
            async with AsyncSessionLocal() as session:
                gif_repo = GifRepository(session)
                
                popular_gifs = await gif_repo.get_popular_gifs(limit)
                popular_gifs = [RawGifOut.model_validate(gif) for gif in popular_gifs]
                
                popular_gifs_out = PopularGifsOut(
                    gifs=popular_gifs, 
                    count=len(popular_gifs)
                )

                await redis.set("popular:gifs", popular_gifs_out.model_dump_json())
                logger.info("Popular GIFs updated")
        except asyncio.CancelledError:
            logger.debug("Stopping popular GIFs updating task...")
            raise 
        except Exception:
            logger.exception("Error when update popular GIFs")

        await asyncio.sleep(recalc_after)
