# Task 19 — app/services/cache_service.py

## What it does

Support service. Wraps fastapi-cache2's `FastAPICache.clear()` to provide typed, named invalidation functions. Called by batch_service, prediction_service, and user_service after every successful commit. Never called by routers or repositories.

---

## Functions

| Function | Clears |
|---|---|
| `invalidate_batch(batch_id)` | Cache for `GET /batches/{batch_id}` |
| `invalidate_user(user_id)` | Cache for `GET /users/{user_id}` / `GET /me` |
| `invalidate_predictions()` | Cache for `GET /predictions/recent` |

---

## Namespace contract — CRITICAL for Ali

fastapi-cache2 uses namespace strings to group and clear cache entries. The namespaces defined here **must match** what Ali uses in his `@cache()` decorators:

| This service uses | Ali must decorate with |
|---|---|
| `"batch:{batch_id}"` | `@cache(namespace=f"batch:{batch_id}")` |
| `"user:{user_id}"` | `@cache(namespace=f"user:{user_id}")` |
| `"predictions:recent"` | `@cache(namespace="predictions:recent")` |

If the namespace strings don't match, cache invalidation silently does nothing — the cache serves stale data.

---

## Why always called AFTER commit

Cache invalidation order is always:
```
1. session.commit()         ← DB is now updated
2. cache_service.invalidate_*()  ← stale cache cleared
```

If we invalidated before commit and then commit failed, the cache would be cleared and the next request would re-cache the OLD data (since the DB write failed). Invalidating after commit means: worst case, the cache serves stale data for the duration of one more request, then gets refreshed on the next read.

---

## Silent failure on exception

All three functions catch `Exception` and log a warning instead of re-raising. Rationale: cache invalidation failure is not a fatal error. The DB write already committed. The cache will naturally expire via TTL. Re-raising would roll back nothing — the transaction is already committed.

---

## app/core/security.py (written alongside this task)

`app/core/security.py` was written as a prerequisite for user_service (Task 22). It lives in `app/core/` which is Mohamad's domain:

```python
from passlib.context import CryptContext
_pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_password(plain: str) -> str: ...
def verify_password(plain: str, hashed: str) -> bool: ...
```

Uses passlib bcrypt (already in requirements.txt). fastapi-users' UserManager also uses bcrypt via pwdlib — both work against the same bcrypt hashes so the app and fastapi-users are compatible.

---

## Connection check

| Import | From | Status |
|---|---|---|
| `FastAPICache` | `fastapi_cache` | ✓ fastapi-cache2 in requirements.txt |
| No DB session | — | cache_service has no session parameter |
| No domain models | — | cache_service has no return values |
