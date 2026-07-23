from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession
import logging

from app.schemas.tag import PopularTagsOut

logger = logging.getLogger(__name__)


class TagService:
    def __init__(
            self,
            session: AsyncSession,
            redis: Redis,
    ):
        self._session = session
        self._redis = redis

    async def get_popular(
            self
    ) -> PopularTagsOut:
        popular_tags = await self._redis.get("popular:tags")

        if popular_tags is None:
            logger.warning("Cant found popular GIFs")
            return PopularTagsOut(
                tags=set(),
                amount=0
            )

        return PopularTagsOut.model_validate_json(popular_tags)


