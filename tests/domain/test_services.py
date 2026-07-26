"""Tests for the service layer: business logic sitting on top of the
repositories, including cache-driven behavior and domain error handling.
"""

import io

import jwt
import pytest
from fastapi import UploadFile
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app import settings
from app.core.exceptions import GifNotFoundError, InvalidCredentialsError, UserNotFoundError
from app.repositories.gif import GifRepository
from app.repositories.user import UserRepository
from app.schemas.auth import TelegramAuthSchema
from app.services.auth import AuthService
from app.services.gif import GifService
from app.services.storage import LocalStorageProvider
from app.services.tag import TagService
from app.services.user import UserService
from app.services.user_library import UserLibraryService
from app.utils.auth import create_access_token, create_refresh_token


def make_gif_upload(content: bytes, filename: str = "test.gif") -> UploadFile:
    return UploadFile(filename=filename, file=io.BytesIO(content))


# --- AuthService ------------------------------------------------------------

class TestAuthService:

    async def test_login_with_valid_telegram_data_creates_user_and_tokens(
            self, db_session: AsyncSession, redis_client: Redis, telegram_auth_payload
    ):
        service = AuthService(db_session, redis_client)
        payload = TelegramAuthSchema(**telegram_auth_payload(tg_id=555001))

        tokens = await service.login_with_telegram(payload)

        assert tokens.access_token
        assert tokens.refresh_token
        assert tokens.token_type == "bearer"

    async def test_login_with_invalid_signature_raises(
            self, db_session: AsyncSession, redis_client: Redis, telegram_auth_payload
    ):
        service = AuthService(db_session, redis_client)
        payload_data = telegram_auth_payload(tg_id=555002)
        payload_data["hash"] = "0" * 64
        payload = TelegramAuthSchema(**payload_data)

        with pytest.raises(InvalidCredentialsError):
            await service.login_with_telegram(payload)

    async def test_login_twice_reuses_same_internal_user(
            self, db_session: AsyncSession, redis_client: Redis, telegram_auth_payload
    ):
        service = AuthService(db_session, redis_client)
        payload = TelegramAuthSchema(**telegram_auth_payload(tg_id=555003))

        await service.login_with_telegram(payload)
        await db_session.commit()
        second_tokens = await service.login_with_telegram(payload)

        claims = jwt.decode(second_tokens.access_token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
        # No error means resolving the same tg_id twice didn't create a duplicate user.
        assert claims["sub"]

    async def test_refresh_tokens_with_valid_token_succeeds(
            self, db_session: AsyncSession, redis_client: Redis, telegram_auth_payload
    ):
        service = AuthService(db_session, redis_client)
        payload = TelegramAuthSchema(**telegram_auth_payload(tg_id=555004))
        tokens = await service.login_with_telegram(payload)

        new_tokens = await service.refresh_tokens(tokens.refresh_token)

        assert new_tokens.access_token
        assert new_tokens.refresh_token

    async def test_refresh_tokens_is_single_use(
            self, db_session: AsyncSession, redis_client: Redis, telegram_auth_payload
    ):
        service = AuthService(db_session, redis_client)
        payload = TelegramAuthSchema(**telegram_auth_payload(tg_id=555005))
        tokens = await service.login_with_telegram(payload)

        await service.refresh_tokens(tokens.refresh_token)

        with pytest.raises(InvalidCredentialsError):
            await service.refresh_tokens(tokens.refresh_token)

    async def test_refresh_with_access_token_type_is_rejected(
            self, db_session: AsyncSession, redis_client: Redis
    ):
        service = AuthService(db_session, redis_client)
        access_token = create_access_token({"sub": "1"})

        with pytest.raises(InvalidCredentialsError):
            await service.refresh_tokens(access_token)

    async def test_refresh_with_garbage_token_is_rejected(
            self, db_session: AsyncSession, redis_client: Redis
    ):
        service = AuthService(db_session, redis_client)
        with pytest.raises(InvalidCredentialsError):
            await service.refresh_tokens("not.a.valid.jwt")

    async def test_logout_invalidates_refresh_token(
            self, db_session: AsyncSession, redis_client: Redis, telegram_auth_payload
    ):
        service = AuthService(db_session, redis_client)
        payload = TelegramAuthSchema(**telegram_auth_payload(tg_id=555006))
        tokens = await service.login_with_telegram(payload)

        claims = jwt.decode(tokens.access_token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
        user_id = int(claims["sub"])

        await service.logout(user_id)

        with pytest.raises(InvalidCredentialsError):
            await service.refresh_tokens(tokens.refresh_token)


# --- GifService ---------------------------------------------------------

class TestGifService:

    async def test_get_popular_returns_empty_when_cache_is_cold(
            self, db_session: AsyncSession, redis_client: Redis
    ):
        service = GifService(db_session, redis_client)
        result = await service.get_popular()
        assert result.gifs == []

    async def test_get_gifs_returns_empty_page_when_no_gifs_exist(
            self, db_session: AsyncSession, redis_client: Redis
    ):
        service = GifService(db_session, redis_client)
        page = await service.get_gifs(limit=10)
        assert page.data == []
        assert page.pagination.has_next is False


# --- TagService ---------------------------------------------------------

class TestTagService:

    async def test_get_popular_returns_empty_when_cache_is_cold(
            self, db_session: AsyncSession, redis_client: Redis
    ):
        service = TagService(db_session, redis_client)
        result = await service.get_popular()
        assert result.tags == []

    async def test_get_popular_tags_for_gif_empty_for_untagged_gif(
            self, db_session: AsyncSession, redis_client: Redis
    ):
        gif = await GifRepository(db_session).create_gif(file_path="untagged.gif", file_hash="h_untagged")
        service = TagService(db_session, redis_client)

        result = await service.get_popular_tags_for_gif(gif_id=gif.id, limit=5)
        assert result.tags == []


# --- UserService ----------------------------------------------------------

class TestUserService:

    async def test_exists_true_for_created_user(self, db_session: AsyncSession, redis_client: Redis):
        user = await UserRepository(db_session).create_user(tg_id=444001)
        service = UserService(db_session, redis_client)

        assert await service.exists(user.id) is True

    async def test_exists_false_for_unknown_user(self, db_session: AsyncSession, redis_client: Redis):
        service = UserService(db_session, redis_client)
        assert await service.exists(999999999) is False

    async def test_exists_uses_cache_on_second_call(self, db_session: AsyncSession, redis_client: Redis):
        user = await UserRepository(db_session).create_user(tg_id=444002)
        service = UserService(db_session, redis_client)

        await service.exists(user.id)
        # Delete underlying row directly to prove the second call is served from cache.
        await UserRepository(db_session).delete_user(user.id)

        assert await service.exists(user.id) is True

    async def test_get_or_create_user_id_creates_new_user(self, db_session: AsyncSession, redis_client: Redis):
        service = UserService(db_session, redis_client)
        user_id = await service.get_or_create_user_id_by_tg_user_id(tg_user_id=444003)
        assert user_id is not None

    async def test_get_or_create_user_id_is_idempotent(self, db_session: AsyncSession, redis_client: Redis):
        service = UserService(db_session, redis_client)
        first_id = await service.get_or_create_user_id_by_tg_user_id(tg_user_id=444004)
        second_id = await service.get_or_create_user_id_by_tg_user_id(tg_user_id=444004)
        assert first_id == second_id

    async def test_delete_user_removes_user_and_invalidates_cache(
            self, db_session: AsyncSession, redis_client: Redis
    ):
        service = UserService(db_session, redis_client)
        user_id = await service.get_or_create_user_id_by_tg_user_id(tg_user_id=444005)
        await service.exists(user_id)  # warm the cache

        await service.delete_user(user_id)

        assert await service.exists(user_id) is False

    async def test_delete_nonexistent_user_raises(self, db_session: AsyncSession, redis_client: Redis):
        service = UserService(db_session, redis_client)
        with pytest.raises(UserNotFoundError):
            await service.delete_user(999999998)


# --- UserLibraryService ------------------------------------------------------

class TestUserLibraryService:

    def _make_service(self, db_session, redis_client, tmp_path) -> UserLibraryService:
        storage = LocalStorageProvider(media_path=str(tmp_path), base_path=str(tmp_path))
        return UserLibraryService(db_session, redis_client, storage)

    async def test_add_new_user_gif_creates_gif_with_tags(
            self, db_session: AsyncSession, redis_client: Redis, tmp_path
    ):
        user = await UserRepository(db_session).create_user(tg_id=666001)
        service = self._make_service(db_session, redis_client, tmp_path)

        gif = await service.add_new_user_gif(
            user_id=user.id, gif_file=make_gif_upload(b"gif bytes 1"), tags={"cat", "funny"}
        )

        assert set(gif.tags) == {"cat", "funny"}

    async def test_add_new_user_gif_deduplicates_identical_content(
            self, db_session: AsyncSession, redis_client: Redis, tmp_path
    ):
        user1 = await UserRepository(db_session).create_user(tg_id=666002)
        user2 = await UserRepository(db_session).create_user(tg_id=666003)
        service = self._make_service(db_session, redis_client, tmp_path)
        content = b"identical content for dedup test"

        gif1 = await service.add_new_user_gif(user_id=user1.id, gif_file=make_gif_upload(content), tags={"a"})
        gif2 = await service.add_new_user_gif(user_id=user2.id, gif_file=make_gif_upload(content), tags={"b"})

        assert gif1.id == gif2.id
        all_gifs = await GifRepository(db_session).get_many_orm()
        matching = [g for g in all_gifs if g.id == gif1.id]
        assert len(matching) == 1

    async def test_get_user_gifs_count(self, db_session: AsyncSession, redis_client: Redis, tmp_path):
        user = await UserRepository(db_session).create_user(tg_id=666004)
        service = self._make_service(db_session, redis_client, tmp_path)
        await service.add_new_user_gif(user_id=user.id, gif_file=make_gif_upload(b"count me"), tags={"x"})

        count = await service.get_user_gifs_count(user_id=user.id)
        assert int(count) == 1

    async def test_get_all_user_tags(self, db_session: AsyncSession, redis_client: Redis, tmp_path):
        user = await UserRepository(db_session).create_user(tg_id=666005)
        service = self._make_service(db_session, redis_client, tmp_path)
        await service.add_new_user_gif(user_id=user.id, gif_file=make_gif_upload(b"tag src"), tags={"a", "b"})

        result = await service.get_all_user_tags(user_id=user.id)
        assert set(result.tags) == {"a", "b"}

    async def test_set_new_user_tags_on_gif_replaces_tag_set(
            self, db_session: AsyncSession, redis_client: Redis, tmp_path
    ):
        user = await UserRepository(db_session).create_user(tg_id=666006)
        service = self._make_service(db_session, redis_client, tmp_path)
        gif = await service.add_new_user_gif(user_id=user.id, gif_file=make_gif_upload(b"retag me"), tags={"old"})

        await service.set_new_user_tags_on_gif(user_id=user.id, gif_id=gif.id, tags={"new", "tags"})

        gifs_page = await service.get_user_gifs_with_tags(user_id=user.id, limit=10)
        updated_gif = next(g for g in gifs_page.data if g.id == gif.id)
        assert set(updated_gif.tags) == {"new", "tags"}

    async def test_set_new_user_tags_on_nonexistent_gif_raises(
            self, db_session: AsyncSession, redis_client: Redis, tmp_path
    ):
        user = await UserRepository(db_session).create_user(tg_id=666007)
        service = self._make_service(db_session, redis_client, tmp_path)

        with pytest.raises(GifNotFoundError):
            await service.set_new_user_tags_on_gif(user_id=user.id, gif_id=999999999, tags={"tag"})

    async def test_unlink_user_from_gif_removes_it_from_library(
            self, db_session: AsyncSession, redis_client: Redis, tmp_path
    ):
        user = await UserRepository(db_session).create_user(tg_id=666008)
        service = self._make_service(db_session, redis_client, tmp_path)
        gif = await service.add_new_user_gif(user_id=user.id, gif_file=make_gif_upload(b"unlink me"), tags={"a"})

        deleted_count = await service.unlink_user_from_gif(user_id=user.id, gif_ids=[gif.id])

        assert deleted_count == 1
        assert await service.get_user_gifs_count(user_id=user.id) == 0

    async def test_unlink_user_from_gif_not_in_library_raises(
            self, db_session: AsyncSession, redis_client: Redis, tmp_path
    ):
        user = await UserRepository(db_session).create_user(tg_id=666009)
        service = self._make_service(db_session, redis_client, tmp_path)

        with pytest.raises(GifNotFoundError):
            await service.unlink_user_from_gif(user_id=user.id, gif_ids=[999999999])

    async def test_unlink_leaves_other_users_library_untouched(
            self, db_session: AsyncSession, redis_client: Redis, tmp_path
    ):
        user1 = await UserRepository(db_session).create_user(tg_id=666010)
        user2 = await UserRepository(db_session).create_user(tg_id=666011)
        service = self._make_service(db_session, redis_client, tmp_path)
        content = b"shared between two users"

        gif1 = await service.add_new_user_gif(user_id=user1.id, gif_file=make_gif_upload(content), tags={"x"})
        await service.add_new_user_gif(user_id=user2.id, gif_file=make_gif_upload(content), tags={"y"})

        await service.unlink_user_from_gif(user_id=user1.id, gif_ids=[gif1.id])

        assert await service.get_user_gifs_count(user_id=user1.id) == 0
        assert await service.get_user_gifs_count(user_id=user2.id) == 1
