from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession
import logging

from app.core.exceptions import UserNotFoundError
from app.models import User
from app.repositories import UserRepository
from app.schemas.user import UserOut, UserStatus
from app.utils.redis import invalidate_many

logger = logging.getLogger(__name__)


class UserService:
    def __init__(
            self,
            session: AsyncSession,
            redis: Redis,
    ):
        self._session = session
        self._redis = redis
        
        self._alias_cache_ttl = 604800
        
        self._active_status_ttl = 604800
        self._banned_status_ttl = 604800
        self._not_found_status_ttl = 60
        
    @classmethod
    def get_current_user_cache_prefix(
            cls,
            user_id: int
    ) -> str:
        return f"user_id:{user_id}"

    async def exists(
            self,
            user_id: int
    ) -> bool:
        user_status = await self._get_user_status_from_cache(user_id)
        
        if user_status == UserStatus.active:
            return True
        
        user_repository = UserRepository(self._session)
        result = await user_repository.get_one(
            columns=User.id,
            filters={User.id: user_id}
        )
        
        if result:
            await self._update_user_status_in_cache(
                user_id=user_id,
                new_status=UserStatus.active,
                ex=self._active_status_ttl
            )
            return True
        else:
            await self._update_user_status_in_cache(
                user_id=user_id,
                new_status=UserStatus.deleted_or_not_found,
                ex=self._not_found_status_ttl
            )
            return False
        
    async def get_user_info(
            self,
            user_id: int
    ) -> UserOut:
        cache_path = f"{self.get_current_user_cache_prefix(user_id)}:info"
        
        user_info = await self._redis.get(cache_path)
        
        if user_info:
            logger.debug(
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
        logger.debug(
            "Get user info",
            extra={
                "user_id": user_id,
                "source": "database"
            }
        )
        
        await self._redis.set(cache_path, user_info.model_dump_json())
        logger.debug(
            "Set user info in cache",
            extra={
                "user_id": user_id,
            }
        )

        return user_info

    async def get_or_create_user_id_by_tg_user_id(
            self,
            tg_user_id: int
    ) -> int:
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
                new_status=UserStatus.active,
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
        user_repository = UserRepository(self._session)
        
        try:
            deleted = await user_repository.delete_many(user_id)
            
            if deleted is None:
                await self._update_user_status_in_cache(
                    user_id=user_id,
                    new_status=UserStatus.deleted_or_not_found,
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
                tg_user_id=deleted[0].tg_id
            )
            await self._update_user_status_in_cache(
                user_id=user_id,
                new_status=UserStatus.deleted_or_not_found,
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
        objects_count = await invalidate_many(
            redis=self._redis,
            match=self.get_current_user_cache_prefix(user_id)
        )
        await self._redis.delete(self._get_user_alias_cache_path(tg_user_id))
        
        logger.debug(
            f"All user cache  ({objects_count} elements) invalidated",
            extra={
                "user_id": user_id
            }
        )
    
    def _get_user_status_cache_path(
            self,
            user_id: int
    ) -> str:
        return f"{self.get_current_user_cache_prefix(user_id)}:status"
    
    async def _update_user_status_in_cache(
            self,
            user_id: int,
            new_status: UserStatus,
            ex: int
    ):
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
        user_status = await self._redis.get(self._get_user_status_cache_path(user_id))
        
        if user_status is not None:
            logger.debug(
                "Get user status from cache",
                extra={
                    "user_id": user_id,
                }
            )
            return UserStatus(user_status)
        
        return None

    @staticmethod
    def _get_user_alias_cache_path(
            tg_user_id: int
    ) -> str:
        return f"tg_user_id:{tg_user_id}:user_id"
    
    async def _create_user_alias_in_cache(
            self,
            tg_user_id: int,
            user_id: int
    ):
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
        user_id = await self._redis.get(self._get_user_alias_cache_path(tg_user_id))
        
        if user_id is not None:
            logger.debug(
                "Get user_id from cache",
                extra={
                    "user_id": user_id,
                }
            )
            return int(user_id)

        return None
