import hashlib
import hmac
import time
from datetime import datetime, timedelta, timezone
import jwt

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

    # Подготавливаем данные
    data_check_list = [
        f"{k}={v}" for k, v in data.items() 
        if k != "hash" and v is not None
    ]
    data_check_list.sort()
    data_check_string = "\n".join(data_check_list)

    # Хэшируем ключ бота
    secret_key = hashlib.sha256(bot_token.encode()).digest()

    # Вычисляем хэш
    calculated_hash = hmac.new(
        secret_key,
        data_check_string.encode(),
        hashlib.sha256
    ).hexdigest()

    if not hmac.compare_digest(calculated_hash, check_hash):
        return False

    # Не старая ли сессия
    auth_date = data.get("auth_date", 0)
    if time.time() - auth_date > 86400:
        return False

    return True


def create_access_token(
        payload: dict, 
        secret_key: str, 
        algorithm: str, 
        expires_delta: timedelta
) -> str:
    """Создает JWT токен."""
    to_encode = payload.copy()
    expire = datetime.now(timezone.utc) + expires_delta
    to_encode.update({"exp": expire})
    
    return jwt.encode(to_encode, secret_key, algorithm=algorithm)
