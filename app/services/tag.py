from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession
import logging

from app.repositories import TagRepository
from app.schemas.tag import PopularTagsOut, RawTagsOut

logger = logging.getLogger(__name__)


class TagService:
    """Read-side operations for tags, backed by a Redis cache."""
    def __init__(
            self,
            session: AsyncSession,
            redis: Redis,
    ):
        """Initializes the service.

        Args:
            session: The async SQLAlchemy session for tag lookups.
            redis: The Redis client used for caching.
        """
        self._session = session
        self._redis = redis

        self._base_cache_ttl = 180

    async def get_popular(
            self
    ) -> PopularTagsOut:
        """Returns the site-wide popular tags list from cache.

        Like `GifService.get_popular`, this is maintained by a periodic
        background task (`recalculate_popular_tags_loop`) rather than
        queried live. If the cache is empty, an empty result is returned.

        Returns:
            The cached popular tags, or an empty result if nothing is
            cached yet.
        """
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
        """Returns the most-used tags for a single GIF, cached per query.

        Args:
            gif_id: Internal ID of the GIF.
            limit: Maximum number of tags to return.

        Returns:
            The most-used tags for `gif_id`, ordered by usage count
            descending.
        """
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
