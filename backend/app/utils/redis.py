from redis.asyncio import Redis


async def invalidate_many(
        redis: Redis,
        match: str
) -> int:
    """Deletes all Redis keys matching a glob pattern, in batches.

    Uses `SCAN` (via `scan_iter`) rather than `KEYS`, so it doesn't block
    Redis while iterating a large keyspace, and `UNLINK` rather than
    `DEL`, so the actual memory reclaim happens asynchronously on the
    server.

    Note:
        This is not atomic — keys created after the scan begins but
        matching `match` may or may not be included, and keys can in
        theory be deleted by other clients between being scanned and
        unlinked.

    Args:
        redis: The Redis client to operate on.
        match: Glob-style pattern to match keys against, e.g.
            ``"user_id:42:*"``.

    Returns:
        The number of keys deleted.
    """
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
