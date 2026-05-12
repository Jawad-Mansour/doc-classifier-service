from pydantic import BaseModel, ConfigDict


class UserDomain(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: str
    is_active: bool
    is_superuser: bool
    is_verified: bool
    role: str
