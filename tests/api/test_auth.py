"""Tests for the two authentication mechanisms guarding the API:
the bot's shared `X-Secret-Key` header, and JWT bearer tokens for web users.
"""

import time

import jwt
from httpx import AsyncClient

from app import settings
from app.repositories.user import UserRepository
from app.utils.auth import create_access_token

# --- Bot auth: X-Secret-Key -------------------------------------------------

class TestBotSecretKeyAuth:

    async def test_missing_key_is_rejected(self, client: AsyncClient):
        response = await client.get("/api/v1/bot/users/123456789/tags/all")
        assert response.status_code == 403

    async def test_wrong_key_is_rejected(self, client: AsyncClient):
        response = await client.get(
            "/api/v1/bot/users/123456789/tags/all",
            headers={"X-Secret-Key": "definitely-wrong-key"},
        )
        assert response.status_code == 401

    async def test_correct_key_passes_auth(self, bot_client: AsyncClient):
        response = await bot_client.get("/api/v1/bot/users/123456789/tags/all")
        assert response.status_code != 401
        assert response.status_code != 403


# --- Web auth: JWT bearer ---------------------------------------------------

class TestJWTAuth:

    async def test_missing_token_is_rejected(self, client: AsyncClient):
        response = await client.get("/api/v1/web/users/me")
        assert response.status_code == 403

    async def test_malformed_token_is_rejected(self, client: AsyncClient):
        response = await client.get(
            "/api/v1/web/users/me", headers={"Authorization": "Bearer not-a-real-jwt"}
        )
        assert response.status_code == 401

    async def test_expired_token_is_rejected(self, client: AsyncClient, web_user_id: int):
        expired_token = jwt.encode(
            {
                "sub": str(web_user_id),
                "type": "access",
                "exp": int(time.time()) - 60,
            },
            settings.JWT_SECRET_KEY,
            algorithm=settings.JWT_ALGORITHM,
        )
        response = await client.get(
            "/api/v1/web/users/me", headers={"Authorization": f"Bearer {expired_token}"}
        )
        assert response.status_code == 401

    async def test_token_for_deleted_user_is_rejected(self, client: AsyncClient, db_session):
        user = await UserRepository(db_session).create_user(tg_id=777001)
        await db_session.commit()
        token = create_access_token({"sub": str(user.id)})

        await UserRepository(db_session).delete_user(user.id)
        await db_session.commit()

        response = await client.get(
            "/api/v1/web/users/me", headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 401

    async def test_valid_token_passes_auth(self, web_client: AsyncClient):
        response = await web_client.get("/api/v1/web/users/me")
        assert response.status_code == 200


# --- Full login / refresh / logout flow, over HTTP --------------------------

class TestTelegramLoginFlow:

    async def test_login_with_valid_widget_data_returns_tokens(
            self, client: AsyncClient, telegram_auth_payload
    ):
        response = await client.post(
            "/api/v1/web/auth/telegram", json=telegram_auth_payload(tg_id=778001)
        )
        assert response.status_code == 200
        body = response.json()
        assert "access_token" in body
        assert "refresh_token" in body
        assert body["token_type"] == "bearer"

    async def test_login_with_invalid_signature_returns_401(
            self, client: AsyncClient, telegram_auth_payload
    ):
        payload = telegram_auth_payload(tg_id=778002)
        payload["hash"] = "0" * 64

        response = await client.post("/api/v1/web/auth/telegram", json=payload)
        assert response.status_code == 401

    async def test_refresh_returns_new_token_pair(self, client: AsyncClient, telegram_auth_payload):
        login_response = await client.post(
            "/api/v1/web/auth/telegram", json=telegram_auth_payload(tg_id=778003)
        )
        refresh_token = login_response.json()["refresh_token"]

        response = await client.post(
            "/api/v1/web/auth/refresh", json={"refresh_token": refresh_token}
        )
        assert response.status_code == 200
        assert response.json()["refresh_token"] != refresh_token

    async def test_reusing_refresh_token_is_rejected(self, client: AsyncClient, telegram_auth_payload):
        login_response = await client.post(
            "/api/v1/web/auth/telegram", json=telegram_auth_payload(tg_id=778004)
        )
        refresh_token = login_response.json()["refresh_token"]

        await client.post("/api/v1/web/auth/refresh", json={"refresh_token": refresh_token})
        second_attempt = await client.post(
            "/api/v1/web/auth/refresh", json={"refresh_token": refresh_token}
        )
        assert second_attempt.status_code == 401

    async def test_logout_then_refresh_is_rejected(self, client: AsyncClient, telegram_auth_payload):
        login_response = await client.post(
            "/api/v1/web/auth/telegram", json=telegram_auth_payload(tg_id=778005)
        )
        tokens = login_response.json()

        logout_response = await client.post(
            "/api/v1/web/auth/logout",
            headers={"Authorization": f"Bearer {tokens['access_token']}"},
        )
        assert logout_response.status_code == 204

        refresh_response = await client.post(
            "/api/v1/web/auth/refresh", json={"refresh_token": tokens["refresh_token"]}
        )
        assert refresh_response.status_code == 401
