"""Unit tests for standalone helpers in `app/utils/`."""

import io
import time

import jwt
import pytest
from fastapi import UploadFile
from redis.asyncio import Redis

from app import settings
from app.models import Gif, User
from app.utils.auth import (
    create_access_token,
    create_refresh_token,
    verify_telegram_widget_data,
)
from app.utils.redis import invalidate_many
from app.utils.sqlalchemy_helpers import (
    get_orm_columns,
    is_valid_column_for_model,
    validate_columns_for_model,
)
from app.utils.storage import create_unique_filename_and_hash

# --- verify_telegram_widget_data ------------------------------------------

class TestVerifyTelegramWidgetData:

    def test_valid_signature_is_accepted(self, telegram_auth_payload):
        data = telegram_auth_payload(tg_id=42)
        assert verify_telegram_widget_data(data, settings.BOT_TOKEN) is True

    def test_tampered_field_is_rejected(self, telegram_auth_payload):
        data = telegram_auth_payload(tg_id=42)
        data["id"] = 999999  # signed for a different id
        assert verify_telegram_widget_data(data, settings.BOT_TOKEN) is False

    def test_wrong_bot_token_is_rejected(self, telegram_auth_payload):
        data = telegram_auth_payload(tg_id=42)
        assert verify_telegram_widget_data(data, "some-other-bot-token") is False

    def test_missing_hash_is_rejected(self, telegram_auth_payload):
        data = telegram_auth_payload(tg_id=42)
        del data["hash"]
        assert verify_telegram_widget_data(data, settings.BOT_TOKEN) is False

    def test_expired_auth_date_is_rejected(self, telegram_auth_payload):
        stale_time = int(time.time()) - 86401  # just over 24h ago
        data = telegram_auth_payload(tg_id=42, auth_date=stale_time)
        assert verify_telegram_widget_data(data, settings.BOT_TOKEN) is False

    def test_auth_date_just_within_window_is_accepted(self, telegram_auth_payload):
        recent_time = int(time.time()) - 86300  # just under 24h ago
        data = telegram_auth_payload(tg_id=42, auth_date=recent_time)
        assert verify_telegram_widget_data(data, settings.BOT_TOKEN) is True


# --- create_access_token / create_refresh_token ---------------------------

class TestJWTCreation:

    def test_access_token_has_expected_claims(self):
        token = create_access_token({"sub": "42"})
        payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])

        assert payload["sub"] == "42"
        assert payload["type"] == "access"
        assert "exp" in payload

    def test_refresh_token_has_expected_claims(self):
        token, jti = create_refresh_token({"sub": "42"})
        payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])

        assert payload["sub"] == "42"
        assert payload["type"] == "refresh"
        assert payload["jti"] == jti
        assert "exp" in payload

    def test_refresh_token_jti_is_unique_per_call(self):
        _, jti_a = create_refresh_token({"sub": "1"})
        _, jti_b = create_refresh_token({"sub": "1"})
        assert jti_a != jti_b

    def test_access_and_refresh_tokens_are_distinguishable(self):
        access = create_access_token({"sub": "1"})
        refresh, _ = create_refresh_token({"sub": "1"})
        assert access != refresh

    def test_token_with_wrong_secret_fails_to_decode(self):
        token = create_access_token({"sub": "42"})
        with pytest.raises(jwt.InvalidTokenError):
            jwt.decode(token, "wrong_secret_key_with_length_over_32_bytes", algorithms=[settings.JWT_ALGORITHM])


# --- sqlalchemy_helpers ----------------------------------------------------

class TestSqlalchemyHelpers:

    def test_is_valid_column_for_model_true(self):
        assert is_valid_column_for_model(User.tg_id, User) is True

    def test_is_valid_column_for_model_wrong_model(self):
        assert is_valid_column_for_model(Gif.file_path, User) is False

    def test_is_valid_column_for_model_non_column(self):
        assert is_valid_column_for_model("not_a_column", User) is False

    def test_validate_columns_for_model_accepts_valid_single_column(self):
        validate_columns_for_model(User.tg_id, User)  # should not raise

    def test_validate_columns_for_model_accepts_valid_iterable(self):
        validate_columns_for_model([User.id, User.tg_id], User)  # should not raise

    def test_validate_columns_for_model_rejects_wrong_model_column(self):
        with pytest.raises(ValueError):
            validate_columns_for_model(Gif.file_path, User)

    def test_get_orm_columns_returns_all_model_columns(self):
        columns = get_orm_columns(User)
        column_names = {c.key for c in columns}
        assert column_names == {"id", "tg_id"}


# --- storage.create_unique_filename_and_hash ------------------------------

class TestCreateUniqueFilenameAndHash:

    async def test_same_content_produces_same_hash(self):
        content = b"identical gif bytes"
        file_a = UploadFile(filename="a.gif", file=io.BytesIO(content))
        file_b = UploadFile(filename="b.gif", file=io.BytesIO(content))

        _, hash_a = await create_unique_filename_and_hash(file_a)
        _, hash_b = await create_unique_filename_and_hash(file_b)

        assert hash_a == hash_b

    async def test_different_content_produces_different_hash(self):
        file_a = UploadFile(filename="a.gif", file=io.BytesIO(b"content A"))
        file_b = UploadFile(filename="b.gif", file=io.BytesIO(b"content B"))

        _, hash_a = await create_unique_filename_and_hash(file_a)
        _, hash_b = await create_unique_filename_and_hash(file_b)

        assert hash_a != hash_b

    async def test_filename_preserves_extension(self):
        file = UploadFile(filename="original.mp4", file=io.BytesIO(b"video bytes"))
        filename, file_hash = await create_unique_filename_and_hash(file)

        assert filename == f"{file_hash}.mp4"

    async def test_file_position_is_reset_after_hashing(self):
        content = b"some gif content"
        file = UploadFile(filename="a.gif", file=io.BytesIO(content))

        await create_unique_filename_and_hash(file)

        assert await file.read() == content


# --- redis.invalidate_many --------------------------------------------------

class TestInvalidateMany:

    async def test_deletes_only_matching_keys(self, redis_client: Redis):
        await redis_client.set("user_id:1:status", "active")
        await redis_client.set("user_id:1:info", "{}")
        await redis_client.set("user_id:2:status", "active")

        deleted = await invalidate_many(redis_client, "user_id:1:*")

        assert deleted == 2
        assert await redis_client.get("user_id:1:status") is None
        assert await redis_client.get("user_id:1:info") is None
        assert await redis_client.get("user_id:2:status") == "active"

    async def test_no_matches_deletes_nothing(self, redis_client: Redis):
        deleted = await invalidate_many(redis_client, "nonexistent:*")
        assert deleted == 0
