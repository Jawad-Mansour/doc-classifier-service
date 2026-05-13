"""Mock user service contract."""

from app.api.schemas import UserRoleResponse

async def change_role(user_id: str, role: str) -> UserRoleResponse:
    return UserRoleResponse(id=user_id, role=role)
