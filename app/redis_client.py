import redis

from .config import get_settings


def get_redis() -> redis.Redis:
    settings = get_settings()
    return redis.Redis(
        host=settings.redis_host,
        port=settings.redis_port,
        decode_responses=True,
    )
