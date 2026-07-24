import hashlib
import hmac
import time
from datetime import datetime, timedelta, timezone
import jwt

from app import settings


# TODO: 
def verify_telegram_widget_data(
        data: dict, 
        bot_token: str
) -> bool:
    """
    Проверяет валидность данных, полученных от Telegram Login Widget.
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
    """Создает JWT токен."""
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
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + expires_delta
    to_encode.update({"exp": expire, "type": "refresh"})
    
    return jwt.encode(to_encode, secret_key, algorithm=algorithm)
