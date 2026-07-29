import logging
from datetime import timedelta

import jwt
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import InvalidCredentialsError
from app import settings
from app.schemas.auth import TelegramAuthSchema, TokenResponseSchema
from app.services.user import UserService
from app.utils.auth import (
    create_access_token,
    create_refresh_token,
    verify_telegram_widget_data,
)

logger = logging.getLogger(__name__)


class AuthService:
    """Handles Telegram-based login and JWT access/refresh token lifecycle.

    Refresh tokens are stored in Redis (one active token per user) so a
    token can be invalidated on logout or superseded by a newer one.
    """
    def __init__(
            self,
            session: AsyncSession,
            redis: Redis
    ):
        """Initializes the service.

        Args:
            session: The async SQLAlchemy session for user lookups.
            redis: The Redis client used to store refresh tokens.
        """
        self._session = session
        self._redis = redis

    async def login_with_telegram(
            self,
            auth_data: TelegramAuthSchema
    ) -> TokenResponseSchema:
        """Logs a user in via Telegram Login Widget data, issuing JWTs.

        Verifies the widget's signature and freshness, resolves the
        Telegram user to an internal user (creating one if this is their
        first login), issues a new access/refresh token pair, and stores
        the refresh token's `jti` in Redis, overwriting any previous one
        for this user.

        Args:
            auth_data: The data returned by the Telegram Login Widget.

        Returns:
            The new access and refresh tokens.

        Raises:
            InvalidCredentialsError: If the widget data's signature is
                invalid or has expired.
        """
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

        refresh_token, jti = create_refresh_token(
            data={"sub": str(user_id)},
        )
        
        refresh_token_expires = timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
        await self._redis.set(
            name=self._get_refresh_token_jti_key(user_id),
            value=jti,
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
        """Exchanges a valid refresh token for a new access/refresh pair.

        Validates the token's signature, type, and expiry, then checks
        its `jti` against the one stored in Redis for that user — this
        makes each refresh token single-use and invalidates any older
        one still floating around (e.g. from a previous device).

        Args:
            refresh_token: The refresh token to exchange.

        Returns:
            A new access and refresh token pair.

        Raises:
            InvalidCredentialsError: If the token is malformed, expired,
                not of type "refresh", has no `jti` claim, or its `jti`
                does not match the one currently stored for that user in
                Redis.
        """
        try:
            payload = jwt.decode(
                refresh_token,
                settings.JWT_SECRET_KEY,
                algorithms=[settings.JWT_ALGORITHM]
            )
            user_id: str = payload.get("sub")
            token_type: str = payload.get("type")
            incoming_jti: str = payload.get("jti")

            if not user_id or token_type != "refresh" or not incoming_jti:
                raise InvalidCredentialsError()
            
        except jwt.PyJWTError:
            raise InvalidCredentialsError()

        saved_jti = await self._redis.get(self._get_refresh_token_jti_key(user_id))

        if isinstance(saved_jti, bytes):
            saved_jti = saved_jti.decode("utf-8")

        if not saved_jti or saved_jti != incoming_jti:
            raise InvalidCredentialsError()

        new_access_token = create_access_token(
            data={"sub": user_id},
        )

        new_refresh_token, new_jti = create_refresh_token(
            data={"sub": user_id},
        )
        
        refresh_token_expires = timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
        await self._redis.set(
            name=self._get_refresh_token_jti_key(user_id),
            value=new_jti,
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
        """Logs a user out by invalidating their stored refresh token jti.

        The corresponding access token jti, if still unexpired, remains valid
        until it naturally expires — logout only prevents future refreshes.

        Args:
            user_id: Internal ID of the user to log out.
        """
        await self._redis.delete(self._get_refresh_token_jti_key(user_id))
        
        logger.info(
            "User logout",
            extra={
                "user_id": user_id
            }
        )
        
    @staticmethod
    def _get_refresh_token_jti_key(
            user_id: int | str
    ) -> str:
        """Builds the Redis key under which a user's refresh token JTI is stored.

        Args:
            user_id: Internal ID of the user.

        Returns:
            The Redis key, e.g. ``"refresh_token_jti:42"``.
        """
        return f"refresh_token_jti:{user_id}"
