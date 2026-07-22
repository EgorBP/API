from redis.asyncio import Redis


# TODO
async def invalidate_many(
        redis: Redis,
        match: str
) -> int:
    keys = []
    objects_count = 0
    batch_size = 500

    async for key in redis.scan_iter(match):
        keys.append(key)

        if len(keys) >= batch_size:
            await redis.unlink(*keys)
            objects_count += len(keys)
            keys = []

    if keys:
        objects_count += len(keys)
        await redis.unlink(*keys)
    
    return objects_count
