import logging
from datetime import timedelta
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.auth import TelegramAuthSchema, TokenResponseSchema
from app.services.user import UserService
from app.utils.auth import verify_telegram_widget_data, create_access_token
from app.core.settings import settings
from app.core.exceptions import InvalidCredentialsError


logger = logging.getLogger(__name__)


# TODO
class AuthService:
    def __init__(
            self,
            session: AsyncSession,
            redis: Redis
    ):
        self._session = session
        self._redis = redis

    async def login_with_telegram(
            self, 
            auth_data: TelegramAuthSchema
    ) -> TokenResponseSchema:
        
        user_service = UserService(
            session=self._session,
            redis=self._redis
        )

        if not verify_telegram_widget_data(auth_data.model_dump(), settings.BOT_TOKEN):
            raise InvalidCredentialsError()
        
        tg_user_id = auth_data.id
        
        user_id = await user_service.get_or_create_user_id_by_tg_user_id(tg_user_id) 

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
