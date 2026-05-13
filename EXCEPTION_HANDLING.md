"""
Custom exception handlers (placeholder).

This file documents the pattern for handling exceptions cleanly.
"""

# EXCEPTION HANDLING PATTERN

## Custom Exceptions

```python
# app/exceptions.py

class AppException(Exception):
    """Base exception for the application."""
    def __init__(self, message: str, error_code: str, status_code: int = 400):
        self.message = message
        self.error_code = error_code
        self.status_code = status_code


class UserNotFoundException(AppException):
    def __init__(self, user_id: str):
        super().__init__(
            message=f"User {user_id} not found",
            error_code="USER_NOT_FOUND",
            status_code=404
        )


class InvalidPredictionException(AppException):
    def __init__(self, reason: str):
        super().__init__(
            message=f"Invalid prediction: {reason}",
            error_code="INVALID_PREDICTION",
            status_code=422
        )
```

## Exception Handlers

```python
# app/main.py - Register handlers

from fastapi import Request
from starlette.responses import JSONResponse
from app.exceptions import AppException
from app.api.schemas import ErrorResponse

@app.exception_handler(AppException)
async def app_exception_handler(request: Request, exc: AppException):
    return JSONResponse(
        status_code=exc.status_code,
        content=ErrorResponse(
            detail=exc.message,
            error_code=exc.error_code,
            request_id=getattr(request.state, "request_id", None)
        ).model_dump()
    )
```

## Usage in Service

```python
# app/services/user_service.py

from app.exceptions import UserNotFoundException

class UserService:
    async def get_user(self, user_id: str) -> User:
        user = await self.repo.get_by_id(user_id)
        if not user:
            raise UserNotFoundException(user_id)
        return user
```

## Usage in Router

```python
# app/api/routers/users.py

@router.get("/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: str,
    service: UserServiceDep
):
    # Exception is automatically caught by FastAPI handler
    user = await service.get_user(user_id)
    return UserResponse(**user.dict())
```

## Result

All exceptions automatically return:
```json
{
  "detail": "User abc123 not found",
  "error_code": "USER_NOT_FOUND",
  "request_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

With the correct HTTP status code (404, 422, etc.).
