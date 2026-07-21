from fastapi import APIRouter, Depends

from app.api.dependencies.services import get_auth_service
from app.schemas.auth import TelegramAuthSchema, TokenResponseSchema
from app.services.auth import AuthService


router = APIRouter()


@router.post(
    "/telegram", 
    response_model=TokenResponseSchema
)
async def login_telegram(
    auth_data: TelegramAuthSchema,
    auth_service: AuthService = Depends(get_auth_service),
):
    return await auth_service.login_with_telegram(auth_data)
