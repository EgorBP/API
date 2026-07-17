from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import Depends

from app.api.dependencies.users import get_user_id_or_create_by_tg_user_id
from app.core.database import get_db
from app.services import UserService
from app.core.redis import get_redis

# TODO: update dockstring
async def get_user_service(
        session: AsyncSession = Depends(get_db),
        redis: Redis = Depends(get_redis),
        user_id: int = Depends(get_user_id_or_create_by_tg_user_id),
):
    return UserService(
        session=session,
        redis=redis,
        user_id=user_id
    )
