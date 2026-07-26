import jwt
from fastapi import Security, HTTPException, status, Depends
from fastapi.security import APIKeyHeader, HTTPAuthorizationCredentials, HTTPBearer
import logging

from app.services.user import UserService
from app import settings
from app.api.dependencies.service import get_user_service


logger = logging.getLogger("app.auth")
api_key_header = APIKeyHeader(name="X-Secret-Key", auto_error=True)
security = HTTPBearer()


async def verify_secret_key(key: str = Security(api_key_header)):
    """FastAPI dependency that authenticates internal bot-to-API requests.

    Compares the `X-Secret-Key` header against `settings.BOT_API_SECRET`.
    Used to protect the `/bot` routes, which the Telegram bot calls on
    behalf of users without a user-level JWT.

    Args:
        key: The `X-Secret-Key` header value.

    Returns:
        The verified key.

    Raises:
        HTTPException: 401, if `key` doesn't match
            `settings.BOT_API_SECRET`.
    """
    if key != settings.BOT_API_SECRET:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect auth key"
        )
    return key


async def get_user_id_from_jwt(
        credentials: HTTPAuthorizationCredentials = Depends(security),
        user_service: UserService = Depends(get_user_service)
) -> int:
    """FastAPI dependency that authenticates web requests via a JWT access token.

    Decodes and verifies the Bearer token, extracts the user ID from the
    `sub` claim, and confirms the user still exists before granting
    access — so a token for a since-deleted user is rejected even if
    still cryptographically valid and unexpired.

    Args:
        credentials: The `Authorization: Bearer <token>` credentials.
        user_service: Service used to confirm the user still exists.

    Returns:
        The authenticated user's internal ID.

    Raises:
        HTTPException: 401, if the token is missing, malformed, expired,
            has no `sub` claim, or its `sub` no longer corresponds to an
            existing user.
    """
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
        user_id = payload.get("sub")
        
        if user_id is None:
            raise credentials_exception
        
        user_id = int(user_id)
        if await user_service.exists(user_id):
            return int(user_id)
        else:
            logger.warning(
                "Trying to access user what doesnt exist",
                extra={
                    "user_id": user_id
                }
            )
            raise credentials_exception
        
    except jwt.PyJWTError:
        raise credentials_exception
