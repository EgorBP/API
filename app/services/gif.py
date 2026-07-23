from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession
import logging

from app.schemas.gif import PopularGifsOut

logger = logging.getLogger(__name__)


class GifService:
    def __init__(
            self,
            session: AsyncSession,
            redis: Redis,
    ):
        self._session = session
        self._redis = redis

    async def get_popular(
            self
    ) -> PopularGifsOut:
        popular_gifs = await self._redis.get("popular:gifs")
        
        if popular_gifs is None:
            logger.warning("Cant found popular GIFs")
            return PopularGifsOut(
                gifs=[],
                amount=0
            )
        
        return PopularGifsOut.model_validate_json(popular_gifs)
    
    
