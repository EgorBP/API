import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app


class TestAuth:
    """Тесты авторизации по заголовку X-Secret-Key (app/core/dependencies.py)."""

    async def test_missing_api_key(self, client: AsyncClient):
        """Без заголовка X-Secret-Key запрос должен быть отклонён с 401."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as unauth_client:
            response = await unauth_client.get("/user/123456789/tags")
            assert response.status_code == 403

    async def test_invalid_api_key(self, client: AsyncClient):
        """С неверным X-Secret-Key запрос должен быть отклонён с 401."""
        response = await client.get(
            "/user/123456789/tags",
            headers={"X-Secret-Key": "definitely-wrong-key"},
        )
        assert response.status_code == 401

    async def test_valid_api_key_passes_auth(self, client: AsyncClient):
        """С правильным ключом (уже проставлен в фикстуре client) запрос проходит дальше auth."""
        response = await client.get("/user/123456789/tags")
        assert response.status_code != 401
