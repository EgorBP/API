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
    while True:
        try:
            async with AsyncSessionLocal() as session:
                gif_repo = TagRepository(session)

                popular_tags = await gif_repo.get_popular_tags(limit)

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
