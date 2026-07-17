from fastapi import Depends, HTTPException
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession
import logging

from starlette import status

from app.core.database import get_db
from app.core.redis import get_redis
from app.models import User
from app.repositories import UserRepository

logger = logging.getLogger("app.dependencies.users")

# TODO: update dockstring
async def get_user_id_or_create_by_tg_user_id(
        session: AsyncSession = Depends(get_db),
        redis: Redis = Depends(get_redis),
        user_id: int | None = None,
        tg_user_id: int | None = None
) -> int:
    async def create_user_alias():
        await redis.set(f"tg_user_id:{tg_user_id}", user_id, ex=604800)

        logger.info(
            "Set alias to get user_id using tg_user_id to cache",
            extra={
                "user_id": user_id,
                "tg_user_id": tg_user_id,
            }
        )

    if user_id is not None:
        return user_id
    
    if not tg_user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Bad Request: authorization data was not transmitted."
        ) 
    
    user_id = await redis.get(f"tg_user_id:{tg_user_id}")

    if user_id:
        logger.info(
            "Get user_id using tg_user_id",
            extra={
                "source": "cache",
                "user_id": user_id,
                "tg_user_id": tg_user_id,
            }
        )
        return int(user_id)
    else:
        user_repository = UserRepository(session)
        user_id = await user_repository.get_one(
            columns=User.id,
            filters={User.tg_id: tg_user_id},
            scalar=True
        )

    if user_id:
        logger.info(
            "Get user_id using tg_user_id",
            extra={
                "source": "database",
                "user_id": user_id,
                "tg_user_id": tg_user_id,
            }
        )
    
        await create_user_alias()

        return user_id
    
    else:
        try:
            user = await user_repository.create_user(tg_user_id)
            
            # await session.commit()
            await session.flush()

            user_id = user.id
            logger.info(
                "Create new user",
                extra={
                    "user_id": user_id,
                    "tg_user_id": tg_user_id,
                }
            )
            
            await create_user_alias()

        except Exception:
            await session.rollback()
            logger.exception(
                "Error when create new user via tg_user_id",
                extra={
                    "tg_user_id": tg_user_id,
                }
            )
            raise
