from rq import Queue
from app.infra.queue.redis_client import redis_conn

classification_queue = Queue(
    "classification",
    connection=redis_conn
)