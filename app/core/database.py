from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from app import settings


DATABASE_URL = (
    f"postgresql+asyncpg://"
    f"{settings.POSTGRES_USER}:"
    f"{settings.POSTGRES_PASSWORD}@"
    f"{settings.POSTGRES_HOST}:"
    f"{settings.POSTGRES_PORT}/"
    f"{settings.POSTGRES_DB}"
)

engine = create_async_engine(DATABASE_URL)
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    expire_on_commit=False
)


async def get_db():
    """Yields an async SQLAlchemy session for use as a FastAPI dependency.

    The session is opened for the duration of a single request and closed
    automatically afterwards. Commit and rollback are the caller's
    responsibility.

    Yields:
        AsyncSession: An active database session bound to `engine`.
    """
    async with AsyncSessionLocal() as db:
        yield db
