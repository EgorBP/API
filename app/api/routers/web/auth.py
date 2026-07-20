from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.telegram import verify_telegram_webapp_data
from app.core.security import create_access_token
from app.repositories import UserRepository
from app.db.session import get_db  # твоя сессия

router = APIRouter(prefix="/auth", tags=["Auth"])


class TelegramLoginSchema(BaseModel):
    init_data: str


@router.post("/telegram")
async def login_via_telegram(
        payload: TelegramLoginSchema,
        db: AsyncSession = Depends(get_db)
):
    # 1. Проверяем строку от Telegram
    tg_user = verify_telegram_webapp_data(payload.init_data)
    if not tg_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid Telegram Init Data"
        )

    tg_user_id = tg_user["id"]  # Получили Telegram ID (например: 12345678)

    user_repository = UserRepository(db)

    # 2. Ищем пользователя в нашей БД по tg_user_id
    user = await user_repository.get_one_orm(filters={"tg_user_id": tg_user_id})

    # 3. Если пользователя нет — регистрируем (Upsert / Create)
    if not user:
        user = await user_repository.create(
            {
                "tg_user_id": tg_user_id,
                "username": tg_user.get("username"),
                "first_name": tg_user.get("first_name"),
            }
        )
        await db.commit()

    # 4. Генерируем JWT-токен, зашивая туда НАШ внутренний id из базы (user.id)
    access_token = create_access_token(data={"sub": user.id})

    return {
        "access_token": access_token,
        "token_type": "bearer"
    }
