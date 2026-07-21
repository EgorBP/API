import logging
from datetime import timedelta
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import User
from app.repositories.users import UserRepository
from app.schemas.auth import TelegramAuthSchema, TokenResponseSchema
from app.utils.auth import verify_telegram_widget_data, create_access_token
from app.core.settings import settings
from app.core.exceptions import InvalidCredentialsError


logger = logging.getLogger(__name__)


# TODO
class AuthService:
    def __init__(
            self,
            session: AsyncSession,
    ):
        self._session = session

    async def login_with_telegram(
            self, 
            auth_data: TelegramAuthSchema
    ) -> TokenResponseSchema:
        
        user_repository = UserRepository(self._session)

        if not verify_telegram_widget_data(auth_data.model_dump(), settings.BOT_TOKEN):
            raise InvalidCredentialsError()
        
        tg_user_id = auth_data.id
        
        user_id = await user_repository.get_one(
            columns=User.id,
            filters={User.tg_id: tg_user_id},
            scalar=True
        )
        
        if not user_id:
            try:
                user = await user_repository.create_user(
                    tg_id=tg_user_id
                )
                user_id = user.id
                
                await self._session.commit()

                logger.info(
                    "Create new user",
                    extra={
                        "user_id": user_id,
                        "tg_user_id": tg_user_id,
                    }
                )

            except Exception:
                await self._session.rollback()
                logger.exception(
                    "Error when create new user via Telegram login data",
                    extra={
                        "tg_user_id": tg_user_id,
                    }
                )
                raise

        access_token = create_access_token(
            payload={"sub": str(user_id)},
            secret_key=settings.JWT_SECRET_KEY,
            algorithm=settings.JWT_ALGORITHM,
            expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
        )
        
        logger.info(
            "Create new JWT token",
            extra={
                "tg_user_id": tg_user_id,
                "user_id": user_id,
            }
        )

        return TokenResponseSchema(access_token=access_token)
