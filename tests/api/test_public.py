"""Tests for the public, unauthenticated GIF/tag search API
(`/api/v1/gifs`, `/api/v1/tags`).
"""

from httpx import AsyncClient


class TestPopularGifsEndpoint:

    async def test_empty_when_cache_is_cold(self, client: AsyncClient, seed_gif):
        await seed_gif(tg_id=900001, file_hash="pub_hash_1", tags={"a"})
        response = await client.get("/api/v1/gifs/popular")
        assert response.status_code == 200
        assert response.json()["gifs"] == []


class TestGifSearchEndpoint:

    async def test_search_without_tags_returns_all(self, client: AsyncClient, seed_gif):
        await seed_gif(tg_id=900002, file_hash="pub_hash_2", tags={"cat"})
        await seed_gif(tg_id=900003, file_hash="pub_hash_3", tags={"dog"})

        response = await client.get("/api/v1/gifs", params={"limit": 20})
        assert response.status_code == 200
        assert len(response.json()["data"]) >= 2

    async def test_search_with_single_tag_filters_results(self, client: AsyncClient, seed_gif):
        cat_gif = await seed_gif(tg_id=900004, file_hash="pub_hash_4", tags={"filter_cat"})
        await seed_gif(tg_id=900005, file_hash="pub_hash_5", tags={"filter_dog"})

        response = await client.get("/api/v1/gifs", params={"tags": ["filter_cat"], "limit": 20})
        assert response.status_code == 200
        data = response.json()["data"]
        assert {g["id"] for g in data} == {cat_gif.id}

    async def test_search_with_multiple_tags_requires_all(self, client: AsyncClient, seed_gif):
        both_gif = await seed_gif(tg_id=900006, file_hash="pub_hash_6", tags={"multi_a", "multi_b"})
        await seed_gif(tg_id=900007, file_hash="pub_hash_7", tags={"multi_a"})

        response = await client.get(
            "/api/v1/gifs", params={"tags": ["multi_a", "multi_b"], "limit": 20}
        )
        assert response.status_code == 200
        data = response.json()["data"]
        assert {g["id"] for g in data} == {both_gif.id}

    async def test_search_with_no_matching_tag_returns_empty(self, client: AsyncClient, seed_gif):
        await seed_gif(tg_id=900008, file_hash="pub_hash_8", tags={"existing_tag"})

        response = await client.get("/api/v1/gifs", params={"tags": ["nonexistent_tag"], "limit": 20})
        assert response.status_code == 200
        assert response.json()["data"] == []

    async def test_limit_is_bounded(self, client: AsyncClient):
        too_high = await client.get("/api/v1/gifs", params={"limit": 1000})
        too_low = await client.get("/api/v1/gifs", params={"limit": 0})
        assert too_high.status_code == 422
        assert too_low.status_code == 422

    async def test_cursor_pagination_returns_disjoint_pages(self, client: AsyncClient, seed_gif):
        for i in range(3):
            await seed_gif(tg_id=900010 + i, file_hash=f"pub_hash_page_{i}", tags={"pagination_tag"})

        first_page = await client.get(
            "/api/v1/gifs", params={"tags": ["pagination_tag"], "limit": 1}
        )
        first_data = first_page.json()

        assert first_data["pagination"]["limit"] == 1
        assert first_data["pagination"]["has_next"] is True
        assert first_data["pagination"]["next_cursor"] == first_data["data"][-1]["id"]
        cursor = first_data["pagination"]["next_cursor"]

        second_page = await client.get(
            "/api/v1/gifs", params={"tags": ["pagination_tag"], "limit": 1, "cursor": cursor}
        )
        second_data = second_page.json()

        assert second_data["pagination"]["has_next"] is True
        assert second_data["pagination"]["next_cursor"] == second_data["data"][-1]["id"]

        first_ids = {g["id"] for g in first_data["data"]}
        second_ids = {g["id"] for g in second_data["data"]}
        assert first_ids.isdisjoint(second_ids)

    async def test_pagination_has_next_false_when_items_exactly_fill_the_page(
            self, client: AsyncClient, seed_gif
    ):
        """Edge case: exactly `limit` matching items exist -> no next page."""
        await seed_gif(tg_id=900040, file_hash="pub_hash_edge_exact_1", tags={"edge_exact_tag"})
        await seed_gif(tg_id=900041, file_hash="pub_hash_edge_exact_2", tags={"edge_exact_tag"})

        response = await client.get("/api/v1/gifs", params={"tags": ["edge_exact_tag"], "limit": 2})
        data = response.json()

        assert len(data["data"]) == 2
        assert data["pagination"]["limit"] == 2
        assert data["pagination"]["has_next"] is False
        assert data["pagination"]["next_cursor"] is None

    async def test_pagination_has_next_false_when_fewer_items_than_limit(
            self, client: AsyncClient, seed_gif
    ):
        """Edge case: fewer matching items than `limit` -> no next page."""
        await seed_gif(tg_id=900042, file_hash="pub_hash_edge_fewer", tags={"edge_fewer_tag"})

        response = await client.get("/api/v1/gifs", params={"tags": ["edge_fewer_tag"], "limit": 5})
        data = response.json()

        assert len(data["data"]) == 1
        assert data["pagination"]["has_next"] is False
        assert data["pagination"]["next_cursor"] is None

    async def test_pagination_empty_result_has_next_false(self, client: AsyncClient, seed_gif):
        """Edge case: no matching items at all -> no next page, no cursor."""
        await seed_gif(tg_id=900043, file_hash="pub_hash_edge_empty", tags={"some_other_tag"})

        response = await client.get("/api/v1/gifs", params={"tags": ["truly_nonexistent_tag"], "limit": 20})
        data = response.json()

        assert data["data"] == []
        assert data["pagination"]["has_next"] is False
        assert data["pagination"]["next_cursor"] is None

    async def test_pagination_last_page_after_cursor_has_next_false(
            self, client: AsyncClient, seed_gif
    ):
        """Edge case: 3 items, limit=2 -> second page holds the single
        remaining item and correctly reports there's no third page."""
        for i in range(3):
            await seed_gif(tg_id=900050 + i, file_hash=f"pub_hash_edge_exhaust_{i}", tags={"edge_exhaust_tag"})

        first_page = await client.get("/api/v1/gifs", params={"tags": ["edge_exhaust_tag"], "limit": 2})
        first_data = first_page.json()
        assert len(first_data["data"]) == 2
        assert first_data["pagination"]["has_next"] is True

        second_page = await client.get(
            "/api/v1/gifs",
            params={
                "tags": ["edge_exhaust_tag"],
                "limit": 2,
                "cursor": first_data["pagination"]["next_cursor"],
            },
        )
        second_data = second_page.json()

        assert len(second_data["data"]) == 1
        assert second_data["pagination"]["has_next"] is False
        assert second_data["pagination"]["next_cursor"] is None


class TestPopularTagsForGifEndpoint:

    async def test_returns_tags_for_existing_gif(self, client: AsyncClient, seed_gif):
        gif = await seed_gif(tg_id=900020, file_hash="pub_hash_tags", tags={"tag_one", "tag_two"})

        response = await client.get(f"/api/v1/gifs/{gif.id}/popular/tags")
        assert response.status_code == 200
        assert set(response.json()["tags"]) == {"tag_one", "tag_two"}

    async def test_returns_empty_for_nonexistent_gif(self, client: AsyncClient):
        response = await client.get("/api/v1/gifs/999999999/popular/tags")
        assert response.status_code == 200
        assert response.json()["tags"] == []


class TestPopularTagsEndpoint:

    async def test_empty_when_cache_is_cold(self, client: AsyncClient, seed_gif):
        await seed_gif(tg_id=900030, file_hash="pub_hash_popular_tags", tags={"some_tag"})
        response = await client.get("/api/v1/tags/popular")
        assert response.status_code == 200
        assert response.json()["tags"] == []
