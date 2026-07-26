import hashlib
import hmac
import time
from datetime import datetime, timedelta, timezone
import jwt

from app import settings


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
    if time.time() - auth_date > 86400:
        return False

    return True


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
    expire = datetime.now(timezone.utc) + expires_delta
    to_encode.update({"exp": expire, "type": "access"})
    
    return jwt.encode(to_encode, secret_key, algorithm=algorithm)


def create_refresh_token(
        data: dict,
        secret_key: str = settings.JWT_SECRET_KEY,
        algorithm: str = settings.JWT_ALGORITHM,
        expires_delta: timedelta = timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
) -> str:
    """Creates a signed JWT refresh token.

    Adds `exp` and `type: "refresh"` claims to `data` before signing.
    Unlike an access token, a refresh token is only valid if it also
    matches the one currently stored for that user in Redis (see
    `AuthService`).

    Args:
        data: Claims to encode into the token, e.g. ``{"sub": str(user_id)}``.
        secret_key: Key used to sign the token.
        algorithm: JWT signing algorithm.
        expires_delta: How long the token remains valid for.

    Returns:
        The encoded JWT.
    """
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + expires_delta
    to_encode.update({"exp": expire, "type": "refresh"})
    
    return jwt.encode(to_encode, secret_key, algorithm=algorithm)
