from redis.asyncio import ConnectionPool, Redis
from fastapi import Request
from app import settings


async def create_redis_client() -> Redis:
    """Создает пул и возвращает клиент Redis."""
    pool = ConnectionPool(
        host=settings.REDIS_HOST,
        port=settings.POSTGRES_PORT,
        decode_responses=True,
        max_connections=20
    )
    return Redis(connection_pool=pool)


async def close_redis_client(redis: Redis):
    """Правильно закрывает клиент и пул соединений."""
    pool = redis.connection_pool
    await redis.aclose()
    if pool:
        await pool.disconnect()


async def get_redis(request: Request) -> Redis:
    """Зависимость (Dependency) для получения Redis в эндпоинтах."""
    return request.app.state.redis
