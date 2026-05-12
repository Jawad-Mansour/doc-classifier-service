# Task 8 — app/domain/user.py

## What it does

Defines `UserDomain`, a Pydantic model that represents a user as returned by the service layer. Services hydrate this from a SQLAlchemy ORM `User` row and return it to routers. Routers never touch ORM objects directly — they work with domain models.

---

## Why a separate domain model from the ORM model

The ORM `User` inherits from `SQLAlchemyBaseUserTable` which carries `hashed_password`. Returning the ORM object from a service would risk accidentally exposing the hash (e.g. if a router serializes it). The domain model explicitly lists what is safe to return.

---

## Design decisions

### `from_attributes=True`
```python
model_config = ConfigDict(from_attributes=True)
```
Allows `UserDomain.model_validate(orm_user_instance)` — Pydantic reads attributes off the ORM object instead of expecting a dict. This is the standard pattern for SQLAlchemy + Pydantic v2.

### `role: str` not `role: UserRole`
The ORM stores role as a plain string. Using `str` here means the domain model works without an enum coercion step. Services that need to compare roles import `UserRole` from `constants.py` themselves.

### No `hashed_password`
Intentionally absent. The hash is an internal implementation detail of the auth layer (fastapi-users). No service or router should ever need it.

---

## Usage pattern

```python
from app.db.models import User as UserORM
from app.domain.user import UserDomain

# In a repository or service, after fetching from DB:
orm_row: UserORM = await session.get(UserORM, user_id)
domain: UserDomain = UserDomain.model_validate(orm_row)
return domain
```

---

## Who uses this

| Who | Where | What they need |
|---|---|---|
| Ali | `app/api/routers/users.py` | Return type for user endpoints (`GET /users/me`, `GET /users/{id}`) |
| Mohamad | `app/services/user_service.py` | Return type from `get_user()`, `list_users()` |
| Mohamad | `app/repositories/user_repo.py` | Output of `get_by_id()`, `get_by_email()` |

---

## What it does NOT do

- No `UserCreate` / `UserUpdate` schemas — those are handled by fastapi-users' built-in schemas (Ali's router task)
- No validation beyond Pydantic type coercion — email format validation is fastapi-users' job at registration time
