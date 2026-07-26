"""Shared pytest fixtures.

Postgres and Redis run in throwaway Docker containers managed by
``testcontainers`` for the whole test session (no ``docker compose`` needed
locally -- just ``uv run pytest``, with Docker running). The schema is
created once per session; each test gets its own isolated transaction
(rolled back via a SAVEPOINT) instead of a freshly recreated schema, plus
HTTP clients pre-authenticated for the bot and web auth flows.
"""

import hashlib
import hmac
import itertools
import random
import time
from typing import AsyncGenerator, Callable

import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool
from testcontainers.community.postgres import PostgresContainer
from testcontainers.community.redis import RedisContainer

from app import settings
from app.api.dependencies.service import get_user_library_service
from app.core.database import get_db
from app.core.redis import get_redis
from app.main import app
from app.models import Base, Gif
from app.repositories.user import UserRepository
from app.services.storage import LocalStorageProvider
from app.services.user_library import UserLibraryService
from app.utils.auth import create_access_token
from tests.helpers import seed_gif_with_tags


# --- Containers (one pair for the whole test session) ---------------------

@pytest.fixture(scope="session")
def postgres_container():
    """Spins up one throwaway Postgres container for the whole test session."""
    with PostgresContainer("postgres:17", driver="asyncpg") as postgres:
        yield postgres


@pytest.fixture(scope="session")
def redis_container():
    """Spins up one throwaway Redis container for the whole test session."""
    with RedisContainer("redis:7-alpine") as redis:
        yield redis


# --- Database ---------------------------------------------------------------

@pytest_asyncio.fixture(scope="session", loop_scope="session")
async def test_engine(postgres_container) -> AsyncGenerator[AsyncEngine, None]:
    """Creates the schema once for the whole test session.

    Per-test isolation is handled by `db_session` via a transaction +
    SAVEPOINT rollback (see below), so `create_all`/`drop_all` only run once
    for the entire suite instead of once per test -- that repeated DDL was
    the main cost of the previous, function-scoped version of this fixture.
    """
    engine = create_async_engine(postgres_container.get_connection_url(), poolclass=NullPool)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    await engine.dispose()


@pytest.fixture
async def db_session(test_engine: AsyncEngine) -> AsyncGenerator[AsyncSession, None]:
    """Provides a database session scoped to a single test.

    Each test gets its own connection and an outer transaction. The session
    is bound to that connection with `join_transaction_mode=
    "create_savepoint"`, so any `session.commit()` made by the code under
    test only releases a SAVEPOINT rather than the outer transaction. After
    the test, the outer transaction is rolled back, undoing everything the
    test did -- no table drop/recreate needed between tests, and no risk of
    one test's data leaking into the next.
    """
    connection = await test_engine.connect()
    outer_transaction = await connection.begin()

    session_maker = async_sessionmaker(
        bind=connection,
        class_=AsyncSession,
        expire_on_commit=False,
        join_transaction_mode="create_savepoint",
    )

    async with session_maker() as session:
        yield session

    await outer_transaction.rollback()
    await connection.close()


# --- Redis --------------------------------------------------------------

@pytest.fixture
async def redis_client(redis_container) -> AsyncGenerator[Redis, None]:
    """Provides a Redis client against the shared container, flushed before and after."""
    redis = Redis(
        host=redis_container.get_container_host_ip(),
        port=int(redis_container.get_exposed_port(6379)),
        decode_responses=True,
    )

    await redis.flushdb()

    yield redis

    await redis.flushdb()
    await redis.aclose()


# --- HTTP clients ---------------------------------------------------------

@pytest.fixture
async def client(db_session, redis_client, tmp_path) -> AsyncGenerator[AsyncClient, None]:
    """Unauthenticated HTTP client with DB/Redis/storage dependencies overridden.

    File uploads are written under `tmp_path` instead of the real
    `settings.MEDIA_DIR`, so running the test suite never touches actual
    project files.
    """

    async def override_get_db():
        yield db_session

    async def override_get_redis():
        return redis_client

    storage = LocalStorageProvider(media_path=str(tmp_path), base_path=str(tmp_path))
    user_library_service = UserLibraryService(db_session, redis_client, storage)
    
    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_redis] = override_get_redis
    app.dependency_overrides[get_user_library_service] = lambda: user_library_service
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()


@pytest.fixture
async def bot_client(client: AsyncClient) -> AsyncClient:
    """HTTP client pre-authenticated as the Telegram bot (`X-Secret-Key` header)."""
    client.headers["X-Secret-Key"] = settings.BOT_API_SECRET
    return client


@pytest.fixture
def make_access_token() -> Callable[[int], str]:
    """Factory that creates a valid JWT access token for a given internal user ID."""

    def _make(user_id: int) -> str:
        return create_access_token({"sub": str(user_id)})

    return _make


@pytest.fixture
async def web_user_id(db_session: AsyncSession) -> int:
    """Creates a user directly in the database and returns their internal ID."""
    user = await UserRepository(db_session).create_user(tg_id=111000111)
    await db_session.commit()
    return user.id


@pytest.fixture
async def web_client(client: AsyncClient, web_user_id: int, make_access_token) -> AsyncClient:
    """HTTP client pre-authenticated as a freshly created web user."""
    client.headers["Authorization"] = f"Bearer {make_access_token(web_user_id)}"
    client.user_id = web_user_id
    return client


# --- Telegram Login Widget signing (for testing the real login flow) -----

def sign_telegram_auth_data(tg_id: int, **extra) -> dict:
    """Builds Telegram Login Widget payload data with a valid signature.

    Signs the data the same way the real widget does, using the app's own
    `settings.BOT_TOKEN` -- so it verifies successfully against
    `verify_telegram_widget_data` regardless of the token's actual value.
    """
    data = {
        "id": tg_id,
        "first_name": "Test",
        "username": "test_user",
        "auth_date": int(time.time()),
        **extra,
    }

    check_list = sorted(f"{k}={v}" for k, v in data.items() if v is not None)
    check_string = "\n".join(check_list)
    secret_key = hashlib.sha256(settings.BOT_TOKEN.encode()).digest()
    data["hash"] = hmac.new(secret_key, check_string.encode(), hashlib.sha256).hexdigest()

    return data


@pytest.fixture
def telegram_auth_payload() -> Callable[..., dict]:
    """Fixture wrapper around `sign_telegram_auth_data`."""
    return sign_telegram_auth_data


# --- Shared test-data helpers -----------------------------------------------

@pytest.fixture
def unique_tg_id() -> Callable[[], int]:
    """Factory that returns a fresh, unique Telegram ID on every call.

    Counting starts from a random base so hand-picked literal IDs elsewhere
    in the suite can't collide with generated ones. Prefer this over adding
    yet another hardcoded number (e.g. `900042`) when a test just needs
    "some user that doesn't exist yet" and the exact value doesn't matter.
    """
    counter = itertools.count(random.randint(10 ** 7, 2 * 10 ** 7))
    return lambda: next(counter)


@pytest.fixture
def seed_gif(db_session: AsyncSession) -> Callable:
    """Bound shortcut for `tests.helpers.seed_gif_with_tags`.

    Creates a user, a GIF, and links them through the given tags, all in
    one call, e.g.: `gif = await seed_gif(tg_id=1, file_hash="h1", tags={"cat"})`.
    """

    async def _seed(tg_id: int, file_hash: str, tags: set[str]) -> Gif:
        return await seed_gif_with_tags(db_session, tg_id=tg_id, file_hash=file_hash, tags=tags)

    return _seed
