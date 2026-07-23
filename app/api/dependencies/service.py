from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import Depends

from app.core.database import get_db
from app.services import UserLibraryService
from app.core.redis import get_redis
from app.services.auth import AuthService
from app.services.gif import GifService
from app.services.storage import LocalStorageProvider
from app.services.tag import TagService
from app.services.user import UserService


# TODO: update dockstring
async def get_user_library_service(
        session: AsyncSession = Depends(get_db),
        redis: Redis = Depends(get_redis)
):
    return UserLibraryService(
        session=session,
        redis=redis,
        storage=LocalStorageProvider(),
    )


async def get_auth_service(
        session: AsyncSession = Depends(get_db),
        redis: Redis = Depends(get_redis)
):
    return AuthService(
        session=session,
        redis=redis
    )


async def get_user_service(
        session: AsyncSession = Depends(get_db),
        redis: Redis = Depends(get_redis)
):
    return UserService(
        session=session,
        redis=redis
    )


async def get_gif_service(
        session: AsyncSession = Depends(get_db),
        redis: Redis = Depends(get_redis)
):
    return GifService(
        session=session,
        redis=redis
    )


async def get_tag_service(
        session: AsyncSession = Depends(get_db),
        redis: Redis = Depends(get_redis)
):
    return TagService(
        session=session,
        redis=redis
    )
