from httpx import AsyncClient


class TestDevEndpoint:

    async def test_dev_login_not_available(self, client: AsyncClient, seed_gif):
        response = await client.post("/api/v1/dev/auth/94823498")
        assert response.status_code == 404
