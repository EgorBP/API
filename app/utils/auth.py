import hashlib
import hmac
import time
import uuid
from datetime import UTC, datetime, timedelta

import jwt

from app import settings
from app.schemas.auth import TelegramAuthSchema


def verify_telegram_widget_data(
        data: dict, 
        bot_token: str
) -> bool:
    """Verifies the authenticity and freshness of Telegram Login Widget data.

    Recomputes the HMAC-SHA256 signature Telegram specifies for widget
    data (all fields except `hash`, sorted and joined as
    ``"key=value"`` lines, signed with SHA256(bot_token) as the key) and
    compares it to `data["hash"]` in constant time. Also rejects data
    whose `auth_date` is more than 24 hours old.

    Args:
        data: The widget's data, including `hash` and `auth_date`.
        bot_token: The bot's token, used to derive the HMAC secret key.

    Returns:
        True if the signature is valid and `auth_date` is within the last
        24 hours, False otherwise (including when `hash` is missing).

    Example:
        Validating data just received from the widget before creating a
        session for the user::

            if not verify_telegram_widget_data(widget_data, settings.BOT_TOKEN):
                raise InvalidCredentialsError()
    """
    check_hash: str = data.get("hash")
    if not check_hash:
        return False

    data_check_list = [
        f"{k}={v}" for k, v in data.items() 
        if k != "hash" and v is not None
    ]
    data_check_list.sort()
    data_check_string = "\n".join(data_check_list)

    secret_key = hashlib.sha256(bot_token.encode()).digest()

    calculated_hash = hmac.new(
        secret_key,
        data_check_string.encode(),
        hashlib.sha256
    ).hexdigest()

    if not hmac.compare_digest(calculated_hash, check_hash):
        return False

    auth_date = data.get("auth_date", 0)
    return not time.time() - auth_date > 86400


def create_access_token(
        data: dict,
        secret_key: str = settings.JWT_SECRET_KEY,
        algorithm: str = settings.JWT_ALGORITHM,
        expires_delta: timedelta = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
) -> str:
    """Creates a signed JWT access token.

    Adds `exp` and `type: "access"` claims to `data` before signing.

    Args:
        data: Claims to encode into the token, e.g. ``{"sub": str(user_id)}``.
        secret_key: Key used to sign the token.
        algorithm: JWT signing algorithm.
        expires_delta: How long the token remains valid for.

    Returns:
        The encoded JWT.
    """
    to_encode = data.copy()
    expire = datetime.now(UTC) + expires_delta
    to_encode.update({"exp": expire, "type": "access"})
    
    return jwt.encode(to_encode, secret_key, algorithm=algorithm)


def create_refresh_token(
        data: dict,
        secret_key: str = settings.JWT_SECRET_KEY,
        algorithm: str = settings.JWT_ALGORITHM,
        expires_delta: timedelta = timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
) -> tuple[str, str]:
    """Creates a signed JWT refresh token with a unique JTI claim.

    Adds `exp`, `type: "refresh"`, and a unique `jti` (a UUIDv4, distinct
    from any other token ever issued) to `data` before signing. The `jti`
    is what makes each refresh token single-use in practice: the caller
    is expected to store it (not the encoded token itself) and compare
    against it on the next refresh — see `AuthService.refresh_tokens`.

    Args:
        data: Claims to encode into the token, e.g. ``{"sub": str(user_id)}``.
        secret_key: Key used to sign the token.
        algorithm: JWT signing algorithm.
        expires_delta: How long the token remains valid for.

    Returns:
        A tuple of `(encoded_jwt, jti)`.
    """
    to_encode = data.copy()
    expire = datetime.now(UTC) + expires_delta
    token_jti = str(uuid.uuid4())

    to_encode.update({
        "exp": expire,
        "type": "refresh",
        "jti": token_jti,
    })

    token = jwt.encode(to_encode, secret_key, algorithm=algorithm)
    return token, token_jti


def generate_fake_telegram_auth_data(
        user_id: int = 12345678,
        first_name: str = "Test",
        last_name: str | None = "User",
        username: str | None = "test_user",
        photo_url: str | None = None,
        bot_token: str = settings.BOT_TOKEN
) -> TelegramAuthSchema:
    """Generates a fake Telegram authentication payload signed with the bot token.

    Computes a valid HMAC-SHA256 signature for the provided mock Telegram user data
    so that it passes auth signature verification during testing.

    Args:
        user_id: Telegram user ID to embed in the payload.
        first_name: Mock user's first name.
        last_name: Mock user's last name.
        username: Mock user's Telegram username.
        photo_url: Mock user's profile photo URL.
        bot_token: Bot token used to compute the HMAC signature.

    Returns:
        A populated `TelegramAuthSchema` instance with a valid `hash`.
    """
    auth_date = int(time.time())

    raw_data = {
        "id": user_id,
        "first_name": first_name,
        "last_name": last_name,
        "username": username,
        "photo_url": photo_url,
        "auth_date": auth_date,
    }
    filtered_data = {k: v for k, v in raw_data.items() if v is not None}
    
    data_check_list = [f"{k}={v}" for k, v in sorted(filtered_data.items())]
    data_check_string = "\n".join(data_check_list)
       
    secret_key = hashlib.sha256(bot_token.encode("utf-8")).digest()
    
    calculated_hash = hmac.new(
        secret_key, data_check_string.encode("utf-8"), hashlib.sha256
    ).hexdigest()
    
    return TelegramAuthSchema(**filtered_data, hash=calculated_hash)
