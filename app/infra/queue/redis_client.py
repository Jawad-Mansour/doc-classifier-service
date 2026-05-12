from redis import Redis

redis_conn = Redis(
    host="localhost",
    port=6379,
    decode_responses=True
)
