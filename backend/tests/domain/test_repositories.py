"""Tests for the repository layer: generic `_BaseRepository` CRUD behavior
plus the model-specific query methods on each repository.
"""

import pytest
from sqlalchemy.exc import IntegrityError, MultipleResultsFound, NoResultFound
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Gif, Tag, User, UserGifTag
from app.repositories.gif import GifRepository
from app.repositories.tag import TagRepository
from app.repositories.user import UserRepository
from app.repositories.user_gif_tag import UserGifTagRepository
from app.schemas.common import SortOrder

# --- Generic _BaseRepository behavior (exercised via UserRepository) -----

class TestBaseRepositoryCreate:

    async def test_create_one_returns_inserted_row(self, db_session: AsyncSession):
        repo = UserRepository(db_session)
        user = await repo.create_one({User.tg_id: 111})
        assert user.id is not None
        assert user.tg_id == 111

    async def test_create_one_raises_on_conflict_by_default(self, db_session: AsyncSession):
        repo = UserRepository(db_session)
        await repo.create_one({User.tg_id: 222})

        with pytest.raises(IntegrityError):
            await repo.create_one({User.tg_id: 222})

    async def test_create_one_ignore_conflicts_returns_none(self, db_session: AsyncSession):
        repo = UserRepository(db_session)
        await repo.create_one({User.tg_id: 333})

        result = await repo.create_one({User.tg_id: 333}, ignore_conflicts=True)
        assert result is None

    async def test_create_one_rejects_column_from_unrelated_model(self, db_session: AsyncSession):
        repo = UserRepository(db_session)
        with pytest.raises(ValueError):
            await repo.create_one({Gif.file_path: "a.gif"})

    async def test_create_many_inserts_all_rows(self, db_session: AsyncSession):
        repo = UserRepository(db_session)
        users = await repo.create_many([{User.tg_id: 401}, {User.tg_id: 402}])
        assert {u.tg_id for u in users} == {401, 402}

    async def test_create_many_ignore_conflicts_skips_only_duplicates(self, db_session: AsyncSession):
        repo = UserRepository(db_session)
        await repo.create_one({User.tg_id: 501})

        users = await repo.create_many(
            [{User.tg_id: 501}, {User.tg_id: 502}],
            ignore_conflicts=True,
        )
        assert {u.tg_id for u in users} == {502}


class TestBaseRepositoryRead:

    async def test_get_many_filters_with_in(self, db_session: AsyncSession):
        repo = UserRepository(db_session)
        u1 = await repo.create_one({User.tg_id: 601})
        u2 = await repo.create_one({User.tg_id: 602})
        await repo.create_one({User.tg_id: 603})

        rows = await repo.get_many(columns=User.tg_id, filters={User.id: [u1.id, u2.id]}, scalars=True)
        assert set(rows) == {601, 602}

    async def test_get_many_no_filters_returns_all(self, db_session: AsyncSession):
        repo = UserRepository(db_session)
        await repo.create_one({User.tg_id: 701})
        await repo.create_one({User.tg_id: 702})

        rows = await repo.get_many(columns=User.tg_id, scalars=True)
        assert set(rows) >= {701, 702}

    async def test_get_one_returns_none_when_no_match(self, db_session: AsyncSession):
        repo = UserRepository(db_session)
        row = await repo.get_one(filters={User.tg_id: 999999})
        assert row is None

    async def test_get_one_scalar_unwraps_single_column(self, db_session: AsyncSession):
        repo = UserRepository(db_session)
        user = await repo.create_one({User.tg_id: 801})

        result = await repo.get_one(columns=User.id, filters={User.tg_id: 801}, scalar=True)
        assert result == user.id

    async def test_get_many_orm_returns_full_instances(self, db_session: AsyncSession):
        repo = UserRepository(db_session)
        await repo.create_one({User.tg_id: 901})

        rows = await repo.get_many_orm(filters={User.tg_id: 901})
        assert len(rows) == 1
        assert isinstance(rows[0], User)
        assert rows[0].tg_id == 901

    async def test_get_one_orm_returns_none_when_no_match(self, db_session: AsyncSession):
        repo = UserRepository(db_session)
        row = await repo.get_one_orm(filters={User.tg_id: 999998})
        assert row is None

    async def test_get_many_rejects_unrelated_model_column_in_filters(self, db_session: AsyncSession):
        repo = UserRepository(db_session)
        with pytest.raises(ValueError):
            await repo.get_many(filters={Gif.id: 1})


class TestBaseRepositoryUpdate:

    async def test_update_one_changes_values(self, db_session: AsyncSession):
        repo = UserRepository(db_session)
        user = await repo.create_one({User.tg_id: 1001})

        updated = await repo.update_one(values={User.tg_id: 1002}, filters={User.id: user.id})
        assert updated.tg_id == 1002

    async def test_update_one_raises_when_no_row_matches(self, db_session: AsyncSession):
        repo = UserRepository(db_session)
        with pytest.raises(NoResultFound):
            await repo.update_one(values={User.tg_id: 1}, filters={User.id: 99999999})

    async def test_update_one_raises_when_multiple_rows_match(self, db_session: AsyncSession):
        repo = UserRepository(db_session)
        u1 = await repo.create_one({User.tg_id: 1101})
        u2 = await repo.create_one({User.tg_id: 1102})

        with pytest.raises(MultipleResultsFound):
            await repo.update_one(values={User.tg_id: User.tg_id}, filters={User.id: [u1.id, u2.id]})

    async def test_update_one_conflict_raises_integrity_error(self, db_session: AsyncSession):
        repo = UserRepository(db_session)
        user = await repo.create_one({User.tg_id: 1201})
        await repo.create_one({User.tg_id: 1202})

        with pytest.raises(IntegrityError):
            await repo.update_one(values={User.tg_id: 1202}, filters={User.id: user.id})


class TestBaseRepositoryDelete:

    async def test_delete_many_removes_matching_rows(self, db_session: AsyncSession):
        repo = UserRepository(db_session)
        u1 = await repo.create_one({User.tg_id: 1301})
        u2 = await repo.create_one({User.tg_id: 1302})

        deleted = await repo.delete_many(filters={User.id: [u1.id, u2.id]})

        assert {u.tg_id for u in deleted} == {1301, 1302}
        assert await repo.get_one(filters={User.id: u1.id}) is None

    async def test_delete_many_no_match_returns_empty_list(self, db_session: AsyncSession):
        repo = UserRepository(db_session)
        deleted = await repo.delete_many(filters={User.id: 99999999})
        assert deleted == []


# --- GifRepository ----------------------------------------------------------

class TestGifRepository:

    async def test_create_gif_inserts_row(self, db_session: AsyncSession):
        repo = GifRepository(db_session)
        gif = await repo.create_gif(file_path="a.gif", file_hash="hash_a")
        assert gif.file_path == "a.gif"
        assert gif.file_hash == "hash_a"

    async def test_create_gif_conflict_raises_by_default(self, db_session: AsyncSession):
        repo = GifRepository(db_session)
        await repo.create_gif(file_path="b.gif", file_hash="hash_b")

        with pytest.raises(IntegrityError):
            await repo.create_gif(file_path="b.gif", file_hash="hash_b")

    async def test_get_popular_gifs_orders_by_save_count(
            self, db_session: AsyncSession
    ):
        gif_repo = GifRepository(db_session)
        tag_repo = TagRepository(db_session)
        ugt_repo = UserGifTagRepository(db_session)
        user_repo = UserRepository(db_session)

        popular_gif = await gif_repo.create_gif(file_path="popular.gif", file_hash="h_pop")
        unpopular_gif = await gif_repo.create_gif(file_path="unpopular.gif", file_hash="h_unpop")
        tag = await tag_repo.create_tag("t")

        for tg_id in (2001, 2002, 2003):
            user = await user_repo.create_user(tg_id=tg_id)
            await ugt_repo.create_user_gif_tag(user_id=user.id, gif_id=popular_gif.id, tag_id=tag.id)

        user = await user_repo.create_user(tg_id=2004)
        await ugt_repo.create_user_gif_tag(user_id=user.id, gif_id=unpopular_gif.id, tag_id=tag.id)

        results = await gif_repo.get_popular_gifs(limit=2)
        result_ids_in_order = [row[0] for row in results]

        assert result_ids_in_order.index(popular_gif.id) < result_ids_in_order.index(unpopular_gif.id)

    async def test_search_user_gifs_with_tags_requires_all_given_tags(self, db_session: AsyncSession):
        gif_repo = GifRepository(db_session)
        tag_repo = TagRepository(db_session)
        ugt_repo = UserGifTagRepository(db_session)
        user_repo = UserRepository(db_session)

        user = await user_repo.create_user(tg_id=2101)
        gif_both = await gif_repo.create_gif(file_path="both.gif", file_hash="h_both")
        gif_one = await gif_repo.create_gif(file_path="one.gif", file_hash="h_one")
        cat_tag = await tag_repo.create_tag("cat")
        funny_tag = await tag_repo.create_tag("funny")

        await ugt_repo.create_user_gif_tag(user_id=user.id, gif_id=gif_both.id, tag_id=cat_tag.id)
        await ugt_repo.create_user_gif_tag(user_id=user.id, gif_id=gif_both.id, tag_id=funny_tag.id)
        await ugt_repo.create_user_gif_tag(user_id=user.id, gif_id=gif_one.id, tag_id=cat_tag.id)

        results = await gif_repo.search_user_gifs_with_tags(user_id=user.id, tags={"cat", "funny"}, limit=10)

        assert len(results) == 1
        assert results[0][0] == gif_both.id

    async def test_search_user_gifs_with_tags_scoped_to_user(self, db_session: AsyncSession):
        gif_repo = GifRepository(db_session)
        tag_repo = TagRepository(db_session)
        ugt_repo = UserGifTagRepository(db_session)
        user_repo = UserRepository(db_session)

        user1 = await user_repo.create_user(tg_id=2201)
        user2 = await user_repo.create_user(tg_id=2202)
        gif = await gif_repo.create_gif(file_path="shared.gif", file_hash="h_shared")
        tag = await tag_repo.create_tag("shared_tag")

        await ugt_repo.create_user_gif_tag(user_id=user1.id, gif_id=gif.id, tag_id=tag.id)

        user1_results = await gif_repo.search_user_gifs_with_tags(user_id=user1.id, limit=10)
        user2_results = await gif_repo.search_user_gifs_with_tags(user_id=user2.id, limit=10)

        assert len(user1_results) == 1
        assert len(user2_results) == 0

    async def test_search_user_gifs_with_tags_cursor_pagination(self, db_session: AsyncSession):
        gif_repo = GifRepository(db_session)
        tag_repo = TagRepository(db_session)
        ugt_repo = UserGifTagRepository(db_session)
        user_repo = UserRepository(db_session)

        user = await user_repo.create_user(tg_id=2301)
        tag = await tag_repo.create_tag("paginated")
        gif_ids = []
        for i in range(5):
            gif = await gif_repo.create_gif(file_path=f"page_{i}.gif", file_hash=f"h_page_{i}")
            await ugt_repo.create_user_gif_tag(user_id=user.id, gif_id=gif.id, tag_id=tag.id)
            gif_ids.append(gif.id)

        first_page = await gif_repo.search_user_gifs_with_tags(user_id=user.id, limit=2)
        assert len(first_page) == 2

        cursor = first_page[-1][0]
        second_page = await gif_repo.search_user_gifs_with_tags(user_id=user.id, cursor=cursor, limit=2)

        assert all(row[0] < cursor for row in second_page)
        first_page_ids = {row[0] for row in first_page}
        second_page_ids = {row[0] for row in second_page}
        assert first_page_ids.isdisjoint(second_page_ids)

    async def test_search_gifs_by_tags_matches_any_user(self, db_session: AsyncSession):
        gif_repo = GifRepository(db_session)
        tag_repo = TagRepository(db_session)
        ugt_repo = UserGifTagRepository(db_session)
        user_repo = UserRepository(db_session)

        owner = await user_repo.create_user(tg_id=2401)
        gif = await gif_repo.create_gif(file_path="global.gif", file_hash="h_global")
        tag = await tag_repo.create_tag("global_tag")
        await ugt_repo.create_user_gif_tag(user_id=owner.id, gif_id=gif.id, tag_id=tag.id)

        results = await gif_repo.search_gifs_by_tags(tags={"global_tag"}, limit=10)
        assert any(row[0] == gif.id for row in results)

    async def test_search_gifs_by_tags_sort_order(self, db_session: AsyncSession):
        gif_repo = GifRepository(db_session)

        gif1 = await gif_repo.create_gif(file_path="sort1.gif", file_hash="h_sort1")
        gif2 = await gif_repo.create_gif(file_path="sort2.gif", file_hash="h_sort2")

        desc_results = await gif_repo.search_gifs_by_tags(sorting=SortOrder.DESC, limit=100)
        asc_results = await gif_repo.search_gifs_by_tags(sorting=SortOrder.ASC, limit=100)

        desc_ids = [row[0] for row in desc_results]
        asc_ids = [row[0] for row in asc_results]

        assert desc_ids.index(gif1.id) > desc_ids.index(gif2.id)
        assert asc_ids.index(gif1.id) < asc_ids.index(gif2.id)


# --- TagRepository -----------------------------------------------------------

class TestTagRepository:

    async def test_create_tag_raises_on_conflict(self, db_session: AsyncSession):
        repo = TagRepository(db_session)
        await repo.create_tag("reusable")

        with pytest.raises(IntegrityError):
            await repo.create_tag("reusable")

    async def test_fake_upsert_tags_returns_all_requested_tags(self, db_session: AsyncSession):
        repo = TagRepository(db_session)
        existing = await repo.create_tag("existing_tag")

        result = await repo.fake_upsert_tags({"existing_tag", "brand_new_tag"})
        result_values = {t.tag for t in result}

        assert result_values == {"existing_tag", "brand_new_tag"}
        existing_result = next(t for t in result if t.tag == "existing_tag")
        assert existing_result.id == existing.id

    async def test_get_unique_user_tags(self, db_session: AsyncSession):
        tag_repo = TagRepository(db_session)
        ugt_repo = UserGifTagRepository(db_session)
        gif_repo = GifRepository(db_session)
        user_repo = UserRepository(db_session)

        user = await user_repo.create_user(tg_id=2501)
        gif1 = await gif_repo.create_gif(file_path="u1.gif", file_hash="h_u1")
        gif2 = await gif_repo.create_gif(file_path="u2.gif", file_hash="h_u2")
        tag_a = await tag_repo.create_tag("unique_a")
        tag_b = await tag_repo.create_tag("unique_b")

        await ugt_repo.create_user_gif_tag(user_id=user.id, gif_id=gif1.id, tag_id=tag_a.id)
        await ugt_repo.create_user_gif_tag(user_id=user.id, gif_id=gif2.id, tag_id=tag_a.id)
        await ugt_repo.create_user_gif_tag(user_id=user.id, gif_id=gif2.id, tag_id=tag_b.id)

        tags = await tag_repo.get_unique_user_tags(user_id=user.id)
        assert set(tags) == {"unique_a", "unique_b"}

    async def test_get_unique_user_tags_empty_for_user_without_gifs(self, db_session: AsyncSession):
        user_repo = UserRepository(db_session)
        tag_repo = TagRepository(db_session)
        user = await user_repo.create_user(tg_id=2502)

        tags = await tag_repo.get_unique_user_tags(user_id=user.id)
        assert tags == []

    async def test_get_popular_tags_orders_by_usage(self, db_session: AsyncSession):
        tag_repo = TagRepository(db_session)
        ugt_repo = UserGifTagRepository(db_session)
        gif_repo = GifRepository(db_session)
        user_repo = UserRepository(db_session)

        popular_tag = await tag_repo.create_tag("popular")
        rare_tag = await tag_repo.create_tag("rare")
        gif = await gif_repo.create_gif(file_path="pop_tags.gif", file_hash="h_pop_tags")

        for tg_id in (2601, 2602, 2603):
            user = await user_repo.create_user(tg_id=tg_id)
            await ugt_repo.create_user_gif_tag(user_id=user.id, gif_id=gif.id, tag_id=popular_tag.id)

        user = await user_repo.create_user(tg_id=2604)
        await ugt_repo.create_user_gif_tag(user_id=user.id, gif_id=gif.id, tag_id=rare_tag.id)

        results = await tag_repo.get_popular_tags(limit=2)
        assert results.index("popular") < results.index("rare")

    async def test_get_popular_gif_tags_scoped_to_single_gif(self, db_session: AsyncSession):
        tag_repo = TagRepository(db_session)
        ugt_repo = UserGifTagRepository(db_session)
        gif_repo = GifRepository(db_session)
        user_repo = UserRepository(db_session)

        gif_a = await gif_repo.create_gif(file_path="scoped_a.gif", file_hash="h_scoped_a")
        gif_b = await gif_repo.create_gif(file_path="scoped_b.gif", file_hash="h_scoped_b")
        tag = await tag_repo.create_tag("scoped_tag")
        user = await user_repo.create_user(tg_id=2701)

        await ugt_repo.create_user_gif_tag(user_id=user.id, gif_id=gif_a.id, tag_id=tag.id)

        results_a = await tag_repo.get_popular_gif_tags(gif_id=gif_a.id, limit=5)
        results_b = await tag_repo.get_popular_gif_tags(gif_id=gif_b.id, limit=5)

        assert "scoped_tag" in results_a
        assert results_b == []


# --- UserRepository -----------------------------------------------------------

class TestUserRepository:

    async def test_create_user_raises_on_conflict(self, db_session: AsyncSession):
        repo = UserRepository(db_session)
        await repo.create_user(tg_id=2801)

        with pytest.raises(IntegrityError):
            await repo.create_user(tg_id=2801)

    async def test_delete_user_removes_row_and_returns_it(self, db_session: AsyncSession):
        repo = UserRepository(db_session)
        user = await repo.create_user(tg_id=2901)

        deleted = await repo.delete_user(user.id)

        assert deleted.id == user.id
        assert await repo.get_one(filters={User.id: user.id}) is None

    async def test_delete_user_returns_none_when_not_found(self, db_session: AsyncSession):
        repo = UserRepository(db_session)
        deleted = await repo.delete_user(user_id=99999999)
        assert deleted is None

    async def test_delete_user_cascades_to_user_gif_tags(self, db_session: AsyncSession):
        user_repo = UserRepository(db_session)
        gif_repo = GifRepository(db_session)
        tag_repo = TagRepository(db_session)
        ugt_repo = UserGifTagRepository(db_session)

        user = await user_repo.create_user(tg_id=3001)
        gif = await gif_repo.create_gif(file_path="cascade.gif", file_hash="h_cascade")
        tag = await tag_repo.create_tag("cascade_tag")
        await ugt_repo.create_user_gif_tag(user_id=user.id, gif_id=gif.id, tag_id=tag.id)

        await user_repo.delete_user(user.id)
        await db_session.flush()

        remaining_links = await ugt_repo.get_many_orm(filters={UserGifTag.user_id: user.id})
        assert remaining_links == []

    async def test_get_user_gifs_count_counts_distinct_gifs(self, db_session: AsyncSession):
        user_repo = UserRepository(db_session)
        gif_repo = GifRepository(db_session)
        tag_repo = TagRepository(db_session)
        ugt_repo = UserGifTagRepository(db_session)

        user = await user_repo.create_user(tg_id=3101)
        gif = await gif_repo.create_gif(file_path="multi_tag.gif", file_hash="h_multi_tag")
        tag_a = await tag_repo.create_tag("count_a")
        tag_b = await tag_repo.create_tag("count_b")

        # Same GIF, two tags -> should still count as one GIF.
        await ugt_repo.create_user_gif_tag(user_id=user.id, gif_id=gif.id, tag_id=tag_a.id)
        await ugt_repo.create_user_gif_tag(user_id=user.id, gif_id=gif.id, tag_id=tag_b.id)

        count = await user_repo.get_user_gifs_count(user_id=user.id)
        assert count == 1

    async def test_get_user_gifs_count_zero_for_empty_library(self, db_session: AsyncSession):
        user_repo = UserRepository(db_session)
        user = await user_repo.create_user(tg_id=3102)

        count = await user_repo.get_user_gifs_count(user_id=user.id)
        assert count == 0


# --- UserGifTagRepository -----------------------------------------------------

class TestUserGifTagRepository:

    async def test_create_user_gif_tag_raises_on_conflict(self, db_session: AsyncSession):
        user_repo = UserRepository(db_session)
        gif_repo = GifRepository(db_session)
        tag_repo = TagRepository(db_session)
        ugt_repo = UserGifTagRepository(db_session)

        user = await user_repo.create_user(tg_id=3201)
        gif = await gif_repo.create_gif(file_path="link.gif", file_hash="h_link")
        tag = await tag_repo.create_tag("link_tag")

        await ugt_repo.create_user_gif_tag(user_id=user.id, gif_id=gif.id, tag_id=tag.id)

        with pytest.raises(IntegrityError):
            await ugt_repo.create_user_gif_tag(user_id=user.id, gif_id=gif.id, tag_id=tag.id)

    async def test_get_many_with_join_selects_joined_columns(self, db_session: AsyncSession):
        user_repo = UserRepository(db_session)
        gif_repo = GifRepository(db_session)
        tag_repo = TagRepository(db_session)
        ugt_repo = UserGifTagRepository(db_session)

        user = await user_repo.create_user(tg_id=3301)
        gif = await gif_repo.create_gif(file_path="joined.gif", file_hash="h_joined")
        tag = await tag_repo.create_tag("joined_tag")
        await ugt_repo.create_user_gif_tag(user_id=user.id, gif_id=gif.id, tag_id=tag.id)

        result = await ugt_repo.get_many_with_join(
            columns=Tag.tag,
            join_models=Tag,
            filters={UserGifTag.user_id: user.id, UserGifTag.gif_id: gif.id},
            scalars=True,
        )

        assert list(result) == ["joined_tag"]

    async def test_delete_except_tag_ids_keeps_only_specified_tags(self, db_session: AsyncSession):
        user_repo = UserRepository(db_session)
        gif_repo = GifRepository(db_session)
        tag_repo = TagRepository(db_session)
        ugt_repo = UserGifTagRepository(db_session)

        user = await user_repo.create_user(tg_id=3401)
        gif = await gif_repo.create_gif(file_path="replace.gif", file_hash="h_replace")
        tag_keep = await tag_repo.create_tag("keep")
        tag_drop = await tag_repo.create_tag("drop")

        await ugt_repo.create_user_gif_tag(user_id=user.id, gif_id=gif.id, tag_id=tag_keep.id)
        await ugt_repo.create_user_gif_tag(user_id=user.id, gif_id=gif.id, tag_id=tag_drop.id)

        await ugt_repo.delete_except_tag_ids(user_id=user.id, gif_id=gif.id, keep_tag_ids={tag_keep.id})
        await db_session.flush()

        remaining = await ugt_repo.get_many_orm(
            filters={UserGifTag.user_id: user.id, UserGifTag.gif_id: gif.id}
        )
        assert {link.tag_id for link in remaining} == {tag_keep.id}
