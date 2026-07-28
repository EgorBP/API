"""Regression tests for cache-key correctness, and for cache-vs-database
boundaries in the read-heavy services (`GifService`, `TagService`).
"""

from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import UserGifTag
from app.repositories.user_gif_tag import UserGifTagRepository
from app.schemas.common import SortOrder
from app.services.gif import GifService
from app.services.tag import TagService


class TestGifServiceCaching:

    async def test_multi_tag_queries_do_not_collide_in_cache(
            self, db_session: AsyncSession, redis_client: Redis, seed_gif
    ):
        """Regression test for a fixed bug: two different 2+-tag searches used
        to share one malformed cache key (`"...tags:{tags}:..."`, never
        `.format()`-ted), so the second query could get served the first
        query's cached results. Both queries must now return only their own
        matching GIF.
        """
        gif_ab = await seed_gif(tg_id=800001, file_hash="hash_ab", tags={"a", "b"})
        gif_cd = await seed_gif(tg_id=800002, file_hash="hash_cd", tags={"c", "d"})

        service = GifService(db_session, redis_client)

        page_ab = await service.get_gifs(limit=20, tags={"a", "b"})
        page_cd = await service.get_gifs(limit=20, tags={"c", "d"})

        ab_ids = {g.id for g in page_ab.data}
        cd_ids = {g.id for g in page_cd.data}

        assert ab_ids == {gif_ab.id}
        assert cd_ids == {gif_cd.id}
        assert ab_ids.isdisjoint(cd_ids)

    async def test_single_tag_first_page_is_cached(
            self, db_session: AsyncSession, redis_client: Redis, seed_gif
    ):
        gif = await seed_gif(tg_id=800003, file_hash="hash_single", tags={"solo"})
        service = GifService(db_session, redis_client)

        first_call = await service.get_gifs(limit=20, tags={"solo"})
        assert {g.id for g in first_call.data} == {gif.id}

        # Remove the underlying link directly, bypassing the service/cache.
        await UserGifTagRepository(db_session).delete_many(
            filters={UserGifTag.gif_id: gif.id}
        )

        # Same query should still return the cached (now stale) result.
        second_call = await service.get_gifs(limit=20, tags={"solo"})
        assert {g.id for g in second_call.data} == {gif.id}

    async def test_multi_tag_queries_are_not_cached(
            self, db_session: AsyncSession, redis_client: Redis, seed_gif
    ):
        gif = await seed_gif(tg_id=800004, file_hash="hash_multi_nocache", tags={"m1", "m2"})
        service = GifService(db_session, redis_client)

        first_call = await service.get_gifs(limit=20, tags={"m1", "m2"})
        assert {g.id for g in first_call.data} == {gif.id}

        await UserGifTagRepository(db_session).delete_many(
            filters={UserGifTag.gif_id: gif.id}
        )

        # Not cached -> must reflect the deletion immediately.
        second_call = await service.get_gifs(limit=20, tags={"m1", "m2"})
        assert second_call.data == []

    async def test_cursor_queries_are_never_cached(
            self, db_session: AsyncSession, redis_client: Redis, seed_gif
    ):
        service = GifService(db_session, redis_client)
        await seed_gif(tg_id=800005, file_hash="hash_cursor1", tags={"cursor_tag"})
        await seed_gif(tg_id=800006, file_hash="hash_cursor2", tags={"cursor_tag"})

        first_page = await service.get_gifs(limit=1, sorting=SortOrder.DESC)
        cursor = first_page.pagination.next_cursor

        second_page = await service.get_gifs(limit=1, sorting=SortOrder.DESC, cursor=cursor)
        assert {g.id for g in second_page.data}.isdisjoint({g.id for g in first_page.data})

    async def test_get_popular_never_queries_database(
            self, db_session: AsyncSession, redis_client: Redis, seed_gif
    ):
        # A GIF exists in the DB, but the popularity cache was never populated
        # by the background task -> get_popular must still return empty.
        await seed_gif(tg_id=800007, file_hash="hash_popular_cold", tags={"tag"})

        service = GifService(db_session, redis_client)
        result = await service.get_popular()

        assert result.gifs == []


class TestTagServiceCaching:

    async def test_get_popular_never_queries_database(
            self, db_session: AsyncSession, redis_client: Redis, seed_gif
    ):
        await seed_gif(tg_id=800008, file_hash="hash_tag_popular_cold", tags={"some_tag"})

        service = TagService(db_session, redis_client)
        result = await service.get_popular()

        assert result.tags == []

    async def test_popular_tags_for_gif_is_cached_per_gif(
            self, db_session: AsyncSession, redis_client: Redis, seed_gif
    ):
        gif = await seed_gif(tg_id=800009, file_hash="hash_gif_tags_cache", tags={"cached_tag"})
        service = TagService(db_session, redis_client)

        first_call = await service.get_popular_tags_for_gif(gif_id=gif.id, limit=5)
        assert "cached_tag" in first_call.tags

        await UserGifTagRepository(db_session).delete_many(
            filters={UserGifTag.gif_id: gif.id}
        )

        # Same (gif_id, limit) query is cached -> should still see the stale result.
        second_call = await service.get_popular_tags_for_gif(gif_id=gif.id, limit=5)
        assert "cached_tag" in second_call.tags
