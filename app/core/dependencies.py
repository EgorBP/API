from fastapi import Security, HTTPException, status
from fastapi.security import APIKeyHeader
from app import settings


api_key_header = APIKeyHeader(name="X-Secret-Key", auto_error=True)

async def verify_secret_key(key: str = Security(api_key_header)):
    """Сверяет ключ из заголовка с ключом из config.py"""
    if key != settings.BOT_API_SECRET:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Неверный секретный ключ доступа"
        )
    return key
