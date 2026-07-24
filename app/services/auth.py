import jwt
import logging
from datetime import timedelta
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.auth import TelegramAuthSchema, TokenResponseSchema
from app.services.user import UserService
from app.utils.auth import verify_telegram_widget_data, create_access_token, create_refresh_token
from app.core.settings import settings
from app.core.exceptions import InvalidCredentialsError


logger = logging.getLogger(__name__)


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
            data={"sub": str(user_id)},
        )

        refresh_token_expires = timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
        refresh_token = create_refresh_token(
            data={"sub": str(user_id)},
        )

        await self._redis.set(
            name=self._get_refresh_token_path(user_id),
            value=refresh_token,
            ex=refresh_token_expires
        )

        logger.info(
            "Created new Access and Refresh tokens",
            extra={
                "tg_user_id": tg_user_id,
                "user_id": user_id,
            }
        )

        return TokenResponseSchema(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer"
        )

    async def refresh_tokens(
            self, 
            refresh_token: str
    ) -> TokenResponseSchema:
        try:
            payload = jwt.decode(
                refresh_token,
                settings.JWT_SECRET_KEY,
                algorithms=[settings.JWT_ALGORITHM]
            )
            user_id: str = payload.get("sub")
            token_type: str = payload.get("type")

            if not user_id or token_type != "refresh":
                raise InvalidCredentialsError()

        except jwt.PyJWTError:
            raise InvalidCredentialsError()

        saved_token = await self._redis.get(self._get_refresh_token_path(user_id))

        if isinstance(saved_token, bytes):
            saved_token = saved_token.decode("utf-8")

        if not saved_token or saved_token != refresh_token:
            raise InvalidCredentialsError()

        new_access_token = create_access_token(
            data={"sub": user_id},
        )

        new_refresh_token = create_refresh_token(
            data={"sub": user_id},
        )

        refresh_token_expires = timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
        await self._redis.set(
            name=self._get_refresh_token_path(user_id),
            value=new_refresh_token,
            ex=refresh_token_expires
        )

        logger.info(
            "Refreshed JWT tokens",
            extra={
                "user_id": user_id
            }
        )

        return TokenResponseSchema(
            access_token=new_access_token,
            refresh_token=new_refresh_token,
            token_type="bearer"
        )

    async def logout(
            self, 
            user_id: int
    ) -> None:
        await self._redis.delete(self._get_refresh_token_path(user_id))
        
        logger.info(
            "User logged",
            extra={
                "user_id": user_id
            }
        )
        
    @staticmethod
    def _get_refresh_token_path(
            user_id: int | str
    ) -> str:
        return f"refresh_token:{user_id}"
