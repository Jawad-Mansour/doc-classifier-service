from datetime import datetime

from pydantic import BaseModel, ConfigDict


class DocumentDomain(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    batch_id: int
    filename: str
    blob_bucket: str
    blob_path: str
    created_at: datetime
