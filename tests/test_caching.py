import pytest
from httpx import AsyncClient
from app.repository import SearchRepository


class TestCaching:
    """Тесты кэширования в app/services/user_services.py."""

    async def test_second_request_hits_cache_not_db(self, client: AsyncClient, monkeypatch):
        """Второй одинаковый GET не должен идти в SearchRepository — данные берутся из Redis."""
        user_id = 555000111
        gif_id = "cache_test_gif"

        await client.put(f"/user/{user_id}/gif/{gif_id}", json={"tags": ["a", "b"]})

        # Первый GET кладёт результат в кэш
        response1 = await client.get(f"/user/{user_id}/gif/{gif_id}")
        assert response1.status_code == 200

        # Подменяем метод репозитория так, чтобы он падал, если его вызовут повторно —
        # если кэш не сработает, тест провалится
        async def _should_not_be_called(*args, **kwargs):
            raise AssertionError("SearchRepository не должен вызываться — ожидался кэш")

        monkeypatch.setattr(SearchRepository, "search_user_gifs_with_tags", _should_not_be_called)

        response2 = await client.get(f"/user/{user_id}/gif/{gif_id}")
        assert response2.status_code == 200
        assert response2.json()["tags"] == response1.json()["tags"]

    async def test_cache_invalidated_after_update(self, client: AsyncClient):
        """После PUT с новыми тегами кэш должен инвалидироваться — GET отдаёт свежие данные."""
        user_id = 555000222
        gif_id = "cache_invalidate_gif"

        await client.put(f"/user/{user_id}/gif/{gif_id}", json={"tags": ["old"]})
        warm = await client.get(f"/user/{user_id}/gif/{gif_id}")
        assert warm.json()["tags"] == ["old"]

        await client.put(f"/user/{user_id}/gif/{gif_id}", json={"tags": ["new"]})

        fresh = await client.get(f"/user/{user_id}/gif/{gif_id}")
        assert fresh.status_code == 200
        assert fresh.json()["tags"] == ["new"]

    async def test_cache_invalidated_after_delete(self, client: AsyncClient):
        """После DELETE кэш должен инвалидироваться — GET отдаёт 404, а не старые данные."""
        user_id = 555000333
        gif_id = "cache_delete_gif"

        await client.put(f"/user/{user_id}/gif/{gif_id}", json={"tags": ["will_be_deleted"]})
        await client.get(f"/user/{user_id}/gif/{gif_id}")  # прогреваем кэш

        await client.delete(f"/user/{user_id}/gif/{gif_id}")

        response = await client.get(f"/user/{user_id}/gif/{gif_id}")
        assert response.status_code == 404
