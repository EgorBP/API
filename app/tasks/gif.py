import asyncio
from redis.asyncio import Redis
import logging

from app.core.database import AsyncSessionLocal
from app.repositories import GifRepository
from app.schemas.gif import PopularGifsOut, RawGifOut

logger = logging.getLogger(__name__)


async def recalculate_popular_gifs_loop(
        redis: Redis,
        limit: int,
        recalc_after: int
):
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
