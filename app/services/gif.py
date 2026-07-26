import logging

from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories import GifRepository
from app.schemas.common import CursorPaginatedResponse, CursorPaginationMeta, SortOrder
from app.schemas.gif import PopularGifsOut, RawGifOut

logger = logging.getLogger(__name__)


class GifService:
    """Read-side operations for GIFs, backed by a Redis cache.

    Popular GIFs are cached by a background task (see `app.tasks.gif`);
    `get_gifs` caches its own results for a short TTL.
    """
    def __init__(
            self,
            session: AsyncSession,
            redis: Redis,
    ):
        """Initializes the service.

        Args:
            session: The async SQLAlchemy session for GIF lookups.
            redis: The Redis client used for caching.
        """
        self._session = session
        self._redis = redis
        
        self._base_cache_ttl = 60

    async def get_popular(
            self
    ) -> PopularGifsOut:
        """Returns the site-wide popular GIFs list from cache.

        This never queries the database directly — the list is
        maintained by a periodic background task
        (`recalculate_popular_gifs_loop`). If the cache is empty (e.g.
        the background task hasn't run yet), an empty result is returned
        rather than falling back to a live query.

        Returns:
            The cached popular GIFs, or an empty result if nothing is
            cached yet.
        """
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
        """Lists GIFs across all users, optionally filtered by tags.

        Only the first page (no `tags`, or exactly one tag, and no
        `cursor`) is cached, since a cache key that also captured
        multi-tag combinations and cursor values would explode in
        cardinality for little benefit; other queries always hit the
        database.

        Args:
            limit: Maximum number of GIFs to return per page.
            sorting: Sort direction by GIF ID.
            tags: If given, only GIFs tagged with all of these tags are
                returned.
            cursor: If given, continues a previous page from this GIF ID,
                per `sorting`.

        Returns:
            A page of GIFs plus pagination metadata (`has_next`,
            `next_cursor`).
        """
        cache_key = None
        if cursor is None:
            if not tags:
                cache_key = f"gifs:{sorting.value}:tags:all:limit:{limit}"
            elif len(tags) == 1: 
                cache_key = f"gifs:{sorting.value}:tags:{tags!s}:limit:{limit}"
            
            if cache_key is not None:
                gifs = await self._redis.get(cache_key)
                
                if gifs is not None:
                    logger.info(
                        f"Get {sorting.value} gifs",
                        extra={
                            "source": "cache"
                        }
                    )
                    return CursorPaginatedResponse[RawGifOut, int].model_validate_json(gifs)
        
        gif_repo = GifRepository(self._session)
        
        gifs = await gif_repo.search_gifs_by_tags(
            tags=tags,
            sorting=sorting,
            cursor=cursor,
            limit=limit + 1
        )

        has_next = len(gifs) > limit
        gifs = gifs[:limit] if has_next else gifs
        next_cursor = gifs[-1].id if gifs else None
        
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
        
        if cache_key is not None:
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
