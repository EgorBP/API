from redis.asyncio import ConnectionPool, Redis
from fastapi import Request
from app import settings


async def create_redis_client() -> Redis:
    """Creates a connection pool and returns a Redis client.

    The pool is shared across the app instance's lifetime and is expected
    to be closed via `close_redis_client` on shutdown.

    Returns:
        Redis: A client backed by a pool of up to 20 connections, with
        responses decoded to `str`.
    """
    pool = ConnectionPool(
        host=settings.REDIS_HOST,
        port=settings.REDIS_PORT,
        decode_responses=True,
        max_connections=20
    )
    return Redis(connection_pool=pool)


async def close_redis_client(redis: Redis):
    """Properly closes the client and its connection pool.

    Args:
        redis: The Redis client previously returned by
            `create_redis_client`.
    """
    pool = redis.connection_pool
    await redis.aclose()
    if pool:
        await pool.disconnect()


async def get_redis(request: Request) -> Redis:
    """FastAPI dependency that returns the shared Redis client.

    Reads the client stored on `app.state.redis` during the application
    lifespan, so it must not be called before the app has started.

    Args:
        request: The current request, used to access `app.state`.

    Returns:
        Redis: The shared Redis client for this application instance.
    """
    return request.app.state.redis
