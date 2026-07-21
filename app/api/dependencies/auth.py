import jwt
from fastapi import Security, HTTPException, status, Depends
from fastapi.security import APIKeyHeader, HTTPAuthorizationCredentials, HTTPBearer
from app import settings


api_key_header = APIKeyHeader(name="X-Secret-Key", auto_error=True)

security = HTTPBearer()


async def verify_secret_key(key: str = Security(api_key_header)):
    """Сверяет ключ из заголовка с ключом из config.py"""
    if key != settings.BOT_API_SECRET:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect auth key"
        )
    return key


async def get_user_id_from_jwt(
        credentials: HTTPAuthorizationCredentials = Depends(security),
):
    token = credentials.credentials
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Failed to validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM]
        )
        user_id: str = payload.get("sub")
        
        if user_id is None:
            raise credentials_exception
        else:
            return int(user_id)
        
    except jwt.PyJWTError:
        raise credentials_exception
