from fastapi import APIRouter, Depends, status

from app.api.dependencies.auth import get_user_id_from_jwt
from app.api.dependencies.service import get_auth_service
from app.schemas.auth import TelegramAuthSchema, TokenResponseSchema, RefreshTokenRequestSchema
from app.services.auth import AuthService


router = APIRouter()


@router.post(
    "/telegram", 
    response_model=TokenResponseSchema
)
async def login_telegram(
    auth_data: TelegramAuthSchema,
    auth_service: AuthService = Depends(get_auth_service)
):
    return await auth_service.login_with_telegram(auth_data)


@router.post(
    "/refresh",
    response_model=TokenResponseSchema
)
async def refresh_tokens(
    body: RefreshTokenRequestSchema,
    auth_service: AuthService = Depends(get_auth_service)
):
    return await auth_service.refresh_tokens(refresh_token=body.refresh_token)


@router.post(
    "/logout",
    status_code=status.HTTP_204_NO_CONTENT
)
async def logout(
    user_id: int = Depends(get_user_id_from_jwt),
    auth_service: AuthService = Depends(get_auth_service)
):
    await auth_service.logout(user_id=user_id)
