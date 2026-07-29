from fastapi import APIRouter, Depends

from app.api.dependencies.service import get_auth_service
from app.schemas.auth import TokenResponseSchema
from app.services.auth import AuthService
from app.utils.auth import generate_fake_telegram_auth_data

router = APIRouter()


@router.post(
    "/{tg_user_id}", 
    response_model=TokenResponseSchema,
    summary="[DEV] Log in via fake Telegram data"
)
async def dev_login_telegram(
    tg_user_id: int = 12345678,
    auth_service: AuthService = Depends(get_auth_service)
):
    """[DEV ONLY] Logs a user in using generated fake Telegram data, issuing JWTs.

    ### Features:
    - Bypasses real Telegram Login Widget interaction for local testing.
    - Automatically creates the user on their first login.
    - Any existing refresh token for this user is invalidated and replaced.
    """
    auth_data = generate_fake_telegram_auth_data(user_id=tg_user_id)
    return await auth_service.login_with_telegram(auth_data)
