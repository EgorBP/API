from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession
import logging

from app.core.exceptions import GifNotFoundError
from app.repositories import GifRepository
from app.schemas.common import SortOrder, CursorPaginatedResponse, CursorPaginationMeta
from app.schemas.gif import PopularGifsOut, RawGifOut

logger = logging.getLogger(__name__)


class GifService:
    def __init__(
            self,
            session: AsyncSession,
            redis: Redis,
    ):
        self._session = session
        self._redis = redis
        
        self._base_cache_ttl = 60

    async def get_popular(
            self
    ) -> PopularGifsOut:
        popular_gifs = await self._redis.get("popular:gifs")
        
        if popular_gifs is None:
            logger.warning("Cant found popular GIFs")
            return PopularGifsOut(
                gifs=[],
                count=0
            )
        
        return PopularGifsOut.model_validate_json(popular_gifs)
    
    async def get_gifs(
            self,
            limit: int,
            sorting: SortOrder = SortOrder.DESC,
            tags: set[str] | None = None,
            cursor: int | None = None
    ) -> CursorPaginatedResponse[RawGifOut, int]:
        cache_key = f"gifs:{sorting.value}:tags:{{tags}}:limit:{limit}"
        if cursor is None:
            if not tags:
                cache_key = cache_key.format(tags="all")
            elif len(tags) == 1: 
                cache_key = cache_key.format(tags=tags)
            
            gifs = await self._redis.get(cache_key)
            
            if gifs is not None:
                logger.info(
                    f"Get {sorting.value} gifs",
                    extra={
                        "source": "cache"
                    }
                )
                return CursorPaginatedResponse.model_validate_json(gifs)
        
        gif_repo = GifRepository(self._session)
        
        gifs = await gif_repo.search_gifs_by_tags(
            tags=tags,
            sorting=sorting,
            cursor=cursor,
            limit=limit + 1
        )

        has_next = len(gifs) > limit

        if has_next:
            rows = gifs[:limit]
            next_cursor = rows[-1].id
        else:
            next_cursor = None

        gifs_data = [
            RawGifOut.model_validate(gif._mapping)
            for gif in gifs
        ]

        final_data = CursorPaginatedResponse[RawGifOut, int](
            data=gifs_data,
            pagination=CursorPaginationMeta[int](
                limit=limit,
                has_next=has_next,
                next_cursor=next_cursor,
            )
        )
        
        if cursor is None:
            await self._redis.set(cache_key, final_data.model_dump_json(), ex=self._base_cache_ttl)
            logger.debug(
                f"Set new cache for {self._base_cache_ttl}s",
            )
        
        logger.info(
            f"Get {sorting.value} gifs",
            extra={
                "source": "database"
            }
        )

        return final_data
