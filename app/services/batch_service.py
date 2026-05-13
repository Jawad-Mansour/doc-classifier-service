"""Mock batch service contract."""

from datetime import datetime
from app.api.schemas import BatchResponse

async def list_batches() -> list[BatchResponse]:
    return [
        BatchResponse(id="batch_1", name="Batch One", status="pending", created_at=datetime.utcnow()),
        BatchResponse(id="batch_2", name="Batch Two", status="reviewed", created_at=datetime.utcnow()),
    ]

async def get_batch(batch_id: str) -> BatchResponse:
    return BatchResponse(id=batch_id, name="Batch One", status="pending", created_at=datetime.utcnow())
