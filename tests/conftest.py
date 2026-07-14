import pytest
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.pool import NullPool
from httpx import AsyncClient, ASGITransport
from redis.asyncio import Redis
from app.models import Base
from app.main import app
from app.core.database import get_db
from app.core.redis import get_redis
from environs import Env


env = Env()
env.read_env()

# Используем отдельную тестовую БД
TEST_DATABASE_URL = (
    f"postgresql+asyncpg://{env('POSTGRES_USER')}:{env('POSTGRES_PASSWORD')}"
    f"@{env('POSTGRES_HOST')}:{env('POSTGRES_PORT')}/test_{env('POSTGRES_DB')}"
)

# Отдельная logical DB Redis для тестов, чтобы не задевать dev/prod кэш
TEST_REDIS_DB = 15


@pytest.fixture(scope="function")
async def test_engine():
    """Создаём тестовый async engine для каждого теста."""
    engine = create_async_engine(
        TEST_DATABASE_URL,
        poolclass=NullPool,
        echo=False,
    )
    
    # Создаём все таблицы
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    
    yield engine
    
    # Очищаем после теста
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    
    await engine.dispose()


@pytest.fixture(scope="function")
async def db_session(test_engine):
    """Создаём новую сессию для каждого теста."""
    async_session_maker = async_sessionmaker(
        test_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )
    
    async with async_session_maker() as session:
        yield session
        await session.rollback()


@pytest.fixture(scope="function")
async def redis_client():
    """Создаём тестовый Redis клиент в отдельной logical DB и чистим её до/после теста."""
    redis = Redis(
        host=env('REDIS_HOST'),
        port=env.int('REDIS_PORT'),
        db=TEST_REDIS_DB,
        decode_responses=True,
    )

    await redis.flushdb()

    yield redis

    await redis.flushdb()
    await redis.aclose()


@pytest.fixture(scope="function")
async def client(db_session, redis_client):
    """Создаём тестовый HTTP клиент с переопределёнными зависимостями БД и Redis,
    а также заголовком авторизации, который требует verify_secret_key."""

    async def override_get_db():
        yield db_session

    async def override_get_redis():
        return redis_client

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_redis] = override_get_redis

    transport = ASGITransport(app=app)
    async with AsyncClient(
        transport=transport,
        base_url="http://test",
        headers={"X-Secret-Key": env('BOT_API_SECRET')},
    ) as ac:
        yield ac

    app.dependency_overrides.clear()
