"""Mock audit service contract."""

from datetime import datetime
from app.api.schemas import AuditLogResponse

async def list_logs(skip: int = 0, limit: int = 50) -> list[AuditLogResponse]:
    return [
        AuditLogResponse(id="log_1", user_id="admin1", action="update_role", resource="users", timestamp=datetime.utcnow(), details={"role":"reviewer"}),
        AuditLogResponse(id="log_2", user_id="reviewer1", action="review", resource="batches", timestamp=datetime.utcnow(), details={"batch_id":"batch_1"}),
    ][skip:skip+limit]
