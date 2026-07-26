"""FastAPI dependencies that construct request-scoped service instances."""

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


async def get_user_library_service(
        session: AsyncSession = Depends(get_db),
        redis: Redis = Depends(get_redis)
):
    """FastAPI dependency providing a request-scoped `UserLibraryService`.

    Args:
        session: Injected async database session.
        redis: Injected Redis client.

    Returns:
        UserLibraryService: Configured with the local disk storage
        provider.
    """
    return UserLibraryService(
        session=session,
        redis=redis,
        storage=LocalStorageProvider(),
    )


async def get_auth_service(
        session: AsyncSession = Depends(get_db),
        redis: Redis = Depends(get_redis)
):
    """FastAPI dependency providing a request-scoped `AuthService`.

    Args:
        session: Injected async database session.
        redis: Injected Redis client.

    Returns:
        AuthService: Ready to use for the current request.
    """
    return AuthService(
        session=session,
        redis=redis
    )


async def get_user_service(
        session: AsyncSession = Depends(get_db),
        redis: Redis = Depends(get_redis)
):
    """FastAPI dependency providing a request-scoped `UserService`.

    Args:
        session: Injected async database session.
        redis: Injected Redis client.

    Returns:
        UserService: Ready to use for the current request.
    """
    return UserService(
        session=session,
        redis=redis
    )


async def get_gif_service(
        session: AsyncSession = Depends(get_db),
        redis: Redis = Depends(get_redis)
):
    """FastAPI dependency providing a request-scoped `GifService`.

    Args:
        session: Injected async database session.
        redis: Injected Redis client.

    Returns:
        GifService: Ready to use for the current request.
    """
    return GifService(
        session=session,
        redis=redis
    )


async def get_tag_service(
        session: AsyncSession = Depends(get_db),
        redis: Redis = Depends(get_redis)
):
    """FastAPI dependency providing a request-scoped `TagService`.

    Args:
        session: Injected async database session.
        redis: Injected Redis client.

    Returns:
        TagService: Ready to use for the current request.
    """
    return TagService(
        session=session,
        redis=redis
    )
