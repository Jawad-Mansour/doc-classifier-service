from redis import Redis

from app.core.config import settings


redis_conn = Redis(
    host=settings.REDIS_HOST,
    port=settings.REDIS_PORT,
    decode_responses=True,
)