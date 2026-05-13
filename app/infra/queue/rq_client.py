from typing import Any

from rq import Queue

from app.core.config import settings
from app.infra.queue.redis_client import redis_connection


classification_queue = Queue(settings.QUEUE_NAME, connection=redis_connection)


def enqueue_inference_job(payload: dict[str, Any]) -> str:
    from app.workers.inference_worker import classify_document_job

    job_id = str(payload["job_id"]) if payload.get("job_id") else None
    job = classification_queue.enqueue(
        classify_document_job,
        payload,
        job_id=job_id,
    )
    return job.id
