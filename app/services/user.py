import logging

from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import UserNotFoundError
from app.models import User, UserStatus
from app.repositories import UserRepository
from app.schemas.user import UserOut
from app.utils.redis import invalidate_many

logger = logging.getLogger(__name__)


class UserService:
    """User lookups and lifecycle, backed by a multi-layer Redis cache.

    Three independent cache entries are kept per user: an existence
    "status" (`UserStatus`), a Telegram-ID-to-internal-ID alias, and a
    serialized `UserOut` info snapshot — each with its own TTL, so a cold
    cache for one doesn't force recomputing the others.
    """
    
    def __init__(
            self,
            session: AsyncSession,
            redis: Redis,
    ):
        """Initializes the service.

        Args:
            session: The async SQLAlchemy session for user lookups.
            redis: The Redis client used for caching.
        """
        self._session = session
        self._redis = redis
        
        self._alias_cache_ttl = 604800
        
        self._active_status_ttl = 604800
        self._banned_status_ttl = 604800
        self._not_found_status_ttl = 60
        
        self._info_cache_ttl = 604800
        
    @classmethod
    def get_user_cache_prefix(
            cls,
            user_id: int
    ) -> str:
        """Builds the common Redis key prefix used for a user's cache entries.

        Args:
            user_id: Internal ID of the user.

        Returns:
            The prefix, e.g. ``"user_id:42"``.
        """
        return f"user_id:{user_id}"

    async def exists(
            self,
            user_id: int
    ) -> bool:
        """Checks whether a user with the given internal ID exists.

        Consults the cached status first; on a cache miss, queries the
        database and caches the result (as `ACTIVE` or
        `DELETED_OR_NOT_FOUND`) for future calls.

        Args:
            user_id: Internal ID of the user.

        Returns:
            True if the user exists, False otherwise.
        """
        user_status = await self._get_user_status_from_cache(user_id)
        
        if user_status == UserStatus.ACTIVE:
            return True
        elif user_status == UserStatus.DELETED_OR_NOT_FOUND:
            return False
        
        user_repository = UserRepository(self._session)
        result = await user_repository.get_one(
            columns=User.id,
            filters={User.id: user_id}
        )
        
        if result:
            await self._update_user_status_in_cache(
                user_id=user_id,
                new_status=UserStatus.ACTIVE,
                ex=self._active_status_ttl
            )
            return True
        else:
            await self._update_user_status_in_cache(
                user_id=user_id,
                new_status=UserStatus.DELETED_OR_NOT_FOUND,
                ex=self._not_found_status_ttl
            )
            return False
        
    async def get_user_info(
            self,
            user_id: int
    ) -> UserOut:
        """Fetches a user's public info, serving from cache when possible.

        Args:
            user_id: Internal ID of the user.

        Returns:
            The user's info.

        Raises:
            AttributeError: If no user exists with this `user_id` (the
                database lookup returns None and validation against it
                fails) — callers should ensure the user exists first,
                e.g. via `exists`.
        """
        cache_path = f"{self.get_user_cache_prefix(user_id)}:info"
        
        user_info = await self._redis.get(cache_path)
        
        if user_info:
            logger.info(
                "Get user info",
                extra={
                    "user_id": user_id,
                    "source": "cache"
                }
            )
            return UserOut.model_validate_json(user_info)
        
        user_repository = UserRepository(self._session)
        
        user_info = await user_repository.get_one_orm(
            filters={User.id: user_id}
        )
        user_info = UserOut.model_validate(user_info)
        logger.info(
            "Get user info",
            extra={
                "user_id": user_id,
                "source": "database"
            }
        )
        
        await self._redis.set(cache_path, user_info.model_dump_json(), ex=self._info_cache_ttl)
        logger.debug(
            f"Set user info in cache for {self._info_cache_ttl}s",
            extra={
                "user_id": user_id,
            }
        )

        return user_info

    async def get_or_create_user_id_by_tg_user_id(
            self,
            tg_user_id: int
    ) -> int:
        """Resolves a Telegram user ID to an internal user ID, creating one if needed.

        Checks the cached alias first, then the database; if no user
        exists yet for this `tg_user_id`, creates one. This is the
        primary entry point for turning a Telegram identity into an
        internal user record.

        Args:
            tg_user_id: Telegram ID of the user.

        Returns:
            The internal user ID, whether pre-existing or newly created.
        """
        user_id = await self._get_user_id_from_cache_alias(tg_user_id)

        if user_id:
            logger.debug(
                "Get user_id using tg_user_id",
                extra={
                    "source": "cache",
                    "user_id": user_id,
                    "tg_user_id": tg_user_id,
                }
            )
            return int(user_id)
        else:
            user_repository = UserRepository(self._session)
            user_id: int | None = await user_repository.get_one(
                columns=User.id,
                filters={User.tg_id: tg_user_id},
                scalar=True
            )

        if user_id is not None:
            logger.debug(
                "Get user_id using tg_user_id",
                extra={
                    "source": "database",
                    "user_id": user_id,
                    "tg_user_id": tg_user_id,
                }
            )
            
            await self._create_user_alias_in_cache(
                tg_user_id=tg_user_id,
                user_id=user_id
            )
            await self._update_user_status_in_cache(
                user_id=user_id,
                new_status=UserStatus.ACTIVE,
                ex=self._active_status_ttl
            )
            
            return user_id
        
        else:
            try:
                user = await user_repository.create_user(tg_user_id)
                
                await self._session.commit()
                
                user_id: int = user.id
                logger.info(
                    "Create new user",
                    extra={
                        "user_id": user_id,
                        "tg_user_id": tg_user_id,
                    }
                )
                
                await self._create_user_alias_in_cache(
                    tg_user_id=tg_user_id,
                    user_id=user_id
                )
                
                return user_id
            
            except Exception:
                await self._session.rollback()
                logger.exception(
                    "Error when creating new user via tg_user_id",
                    extra={
                        "tg_user_id": tg_user_id,
                    }
                )
                raise
            
    async def delete_user(
            self,
            user_id: int
    ) -> None:
        """Deletes a user and invalidates all of their cached data.

        Args:
            user_id: Internal ID of the user to delete.

        Raises:
            UserNotFoundError: If no user exists with this `user_id`.
        """
        user_repository = UserRepository(self._session)
        
        try:
            deleted = await user_repository.delete_user(user_id)
            
            if deleted is None:
                await self._update_user_status_in_cache(
                    user_id=user_id,
                    new_status=UserStatus.DELETED_OR_NOT_FOUND,
                    ex=self._not_found_status_ttl
                )
                raise UserNotFoundError(user_id)
            
            await self._session.commit()
            logger.info(
                "User deleted",
                extra={
                    "user_id": user_id
                }
            )
            
            await self._invalidate_all_user_cache(
                user_id=user_id,
                tg_user_id=deleted.tg_id
            )
            await self._update_user_status_in_cache(
                user_id=user_id,
                new_status=UserStatus.DELETED_OR_NOT_FOUND,
                ex=self._not_found_status_ttl
            )

        except Exception:
            await self._session.rollback()
            logger.exception(
                "Error when delete user",
                extra={
                    "user_id": user_id
                }
            )
            raise
    
    async def _invalidate_all_user_cache(
            self,
            user_id: int,
            tg_user_id: int
    ) -> None:
        """Removes every cache entry associated with a user.

        Matches and deletes any Redis key containing `user_id` (covering
        the status and info caches, which are keyed by internal ID) and
        separately removes the Telegram-ID alias key, which is keyed by
        `tg_user_id` instead.

        Args:
            user_id: Internal ID of the user.
            tg_user_id: Telegram ID of the user.
        """
        objects_count = await invalidate_many(
            redis=self._redis,
            match=f"*{user_id}*"
        )
        await self._redis.delete(self._get_user_alias_cache_path(tg_user_id))
        
        logger.debug(
            f"All user cache ({objects_count} elements) invalidated",
            extra={
                "user_id": user_id
            }
        )
    
    def _get_user_status_cache_path(
            self,
            user_id: int
    ) -> str:
        """Builds the Redis key for a user's cached existence status.

        Args:
            user_id: Internal ID of the user.

        Returns:
            The Redis key, e.g. ``"user_id:42:status"``.
        """
        return f"{self.get_user_cache_prefix(user_id)}:status"
    
    async def _update_user_status_in_cache(
            self,
            user_id: int,
            new_status: UserStatus,
            ex: int
    ):
        """Writes a user's existence status to cache with a TTL.

        Args:
            user_id: Internal ID of the user.
            new_status: The status to cache.
            ex: Time-to-live for the cache entry, in seconds.
        """
        await self._redis.set(
            self._get_user_status_cache_path(user_id),
            new_status.value,
            ex=ex
        )
        
        logger.info(
            f"New user status: {new_status.value} for {ex}s",
            extra={
                "user_id": user_id
            }
        )
        
    async def _get_user_status_from_cache(
            self,
            user_id: int
    ) -> UserStatus | None:
        """Reads a user's cached existence status, if present.

        Args:
            user_id: Internal ID of the user.

        Returns:
            The cached status, or None on a cache miss.
        """
        user_status = await self._redis.get(self._get_user_status_cache_path(user_id))
        
        if user_status is not None:
            logger.debug(
                "Get user status",
                extra={
                    "source": "cache",
                    "user_id": user_id,
                }
            )
            return UserStatus(user_status)
        
        return None

    @staticmethod
    def _get_user_alias_cache_path(
            tg_user_id: int
    ) -> str:
        """Builds the Redis key for a Telegram-ID-to-internal-ID alias.

        Args:
            tg_user_id: Telegram ID of the user.

        Returns:
            The Redis key, e.g. ``"tg_user_id:123456:user_id"``.
        """
        return f"tg_user_id:{tg_user_id}:user_id"
    
    async def _create_user_alias_in_cache(
            self,
            tg_user_id: int,
            user_id: int
    ):
        """Caches the mapping from a Telegram ID to an internal user ID.

        Args:
            tg_user_id: Telegram ID of the user.
            user_id: Internal ID of the user.
        """
        await self._redis.set(
            self._get_user_alias_cache_path(tg_user_id), 
            user_id, 
            ex=self._alias_cache_ttl
        )
        
        logger.debug(
            "Set alias to get user_id using tg_user_id to cache",
            extra={
                "user_id": user_id,
                "tg_user_id": tg_user_id,
            }
        )
        
    async def _get_user_id_from_cache_alias(
            self,
            tg_user_id: int
    ) -> int | None:
        """Reads a user's cached internal ID by their Telegram ID.

        Args:
            tg_user_id: Telegram ID of the user.

        Returns:
            The cached internal user ID, or None on a cache miss.
        """
        user_id = await self._redis.get(self._get_user_alias_cache_path(tg_user_id))
        
        if user_id is not None:
            logger.debug(
                "Get user_id",
                extra={
                    "source": "cache",
                    "user_id": user_id,
                }
            )
            return int(user_id)

        return None
