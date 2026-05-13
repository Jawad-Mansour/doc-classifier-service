from app.infra.queue.redis_client import redis_conn


def get_cache(key: str):
    return redis_conn.get(key)


def set_cache(key: str, value: str, ttl_seconds: int = 300):
    redis_conn.setex(key, ttl_seconds, value)


def delete_cache(key: str):
    redis_conn.delete(key)