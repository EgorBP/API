from fastapi import APIRouter, Depends, status

from app.api.dependencies.auth import get_user_id_from_jwt
from app.api.dependencies.service import get_auth_service
from app.schemas.auth import (
    RefreshTokenRequestSchema,
    TelegramAuthSchema,
    TokenResponseSchema,
)
from app.services.auth import AuthService

router = APIRouter()


@router.post(
    "/telegram", 
    response_model=TokenResponseSchema,
    summary="Log in via Telegram Login Widget",
    responses={
        status.HTTP_401_UNAUTHORIZED: {
            "description": "Widget signature is invalid, or `auth_date` is older than 24 hours.",
        },
    },
)
async def login_telegram(
    auth_data: TelegramAuthSchema,
    auth_service: AuthService = Depends(get_auth_service)
):
    """Logs a user in using Telegram Login Widget data, issuing JWTs.

    ### Features:
    - Automatically creates the user on their first login.
    - Any existing refresh token for this user is invalidated and
      replaced.
    """
    return await auth_service.login_with_telegram(auth_data)


@router.post(
    "/refresh",
    response_model=TokenResponseSchema,
    summary="Exchange a refresh token for a new token pair",
    responses={
        status.HTTP_401_UNAUTHORIZED: {
            "description": "Token is malformed, expired, not a refresh token, or no longer matches the one on record.",
        },
    },
)
async def refresh_tokens(
    body: RefreshTokenRequestSchema,
    auth_service: AuthService = Depends(get_auth_service)
):
    """Exchanges a valid refresh token for a new access/refresh token pair.

    ### Notes:
    - **Single-use**: exchanging a refresh token invalidates it,
      including for other devices/sessions using an older token.
    """
    return await auth_service.refresh_tokens(refresh_token=body.refresh_token)


@router.post(
    "/logout",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Log out and invalidate the refresh token",
)
async def logout(
    user_id: int = Depends(get_user_id_from_jwt),
    auth_service: AuthService = Depends(get_auth_service)
):
    """Logs the authenticated user out by invalidating their refresh token.

    ### Notes:
    - The current access token, if still unexpired, **remains valid**
      until it naturally expires — this only blocks future refreshes.
    """
    await auth_service.logout(user_id=user_id)
