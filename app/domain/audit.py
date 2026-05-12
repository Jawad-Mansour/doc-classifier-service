from datetime import datetime

from pydantic import BaseModel, ConfigDict


class AuditLogDomain(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    actor: str
    action: str
    target: str
    timestamp: datetime
