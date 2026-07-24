from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession
import logging

from app.core.exceptions import TagNotFoundError
from app.repositories import TagRepository
from app.schemas.tag import PopularTagsOut, RawTagsOut

logger = logging.getLogger(__name__)


class TagService:
    def __init__(
            self,
            session: AsyncSession,
            redis: Redis,
    ):
        self._session = session
        self._redis = redis

        self._base_cache_ttl = 180

    async def get_popular(
            self
    ) -> PopularTagsOut:
        popular_tags = await self._redis.get("popular:tags")

        if popular_tags is None:
            logger.warning("Cant found popular GIFs")
            return PopularTagsOut(
                tags=[],
                count=0
            )

        return PopularTagsOut.model_validate_json(popular_tags)

    async def get_popular_tags_for_gif(
            self,
            gif_id: int,
            limit: int
    ) -> RawTagsOut:
        cache_key = f"gifs:{gif_id}:limit:{limit}"
        log_msg = f"Get {limit} popular tags"
        tags = await self._redis.get(cache_key)

        if tags is not None:
            logger.info(
                log_msg,
                extra={
                    "source": "cache",
                    "gif_id": gif_id
                }
            )
            return RawTagsOut.model_validate_json(tags)

        tag_repo = TagRepository(self._session)

        tags = await tag_repo.get_popular_gif_tags(
            gif_id=gif_id,
            limit=limit
        )

        final_data = RawTagsOut(
            tags=tags,
            count=len(tags)
        )

        await self._redis.set(cache_key, final_data.model_dump_json(), ex=self._base_cache_ttl)
        
        logger.debug(
            f"Set new cache for {self._base_cache_ttl}s",
        )
        logger.info(
            log_msg,
            extra={
                "source": "database",
                "gif_id": gif_id
            }
        )

        return final_data
