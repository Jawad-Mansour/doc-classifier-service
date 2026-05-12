# Task 13 — app/repositories/user_repository.py

## What it does

SQL-only functions for the `users` table. No business logic. The service layer calls these and wraps them with guards, audit calls, and cache invalidation.

---

## Functions

| Function | SQL | Returns |
|---|---|---|
| `get_by_id(session, user_id)` | `session.get(User, user_id)` | `User \| None` |
| `get_by_email(session, email)` | `SELECT ... WHERE email = ?` | `User \| None` |
| `count_by_role(session, role)` | `SELECT COUNT(*) WHERE role = ?` | `int` |
| `create(session, email, hashed_password, role)` | `INSERT INTO users ...` | `User` |
| `update_role(session, user_id, new_role)` | mutates `user.role`, flush | `User \| None` |

---

## `count_by_role` — why it exists

Not in the original task description but required by `user_service.toggle_role()`:

```python
count = await user_repo.count_by_role(session, UserRole.ADMIN)
if count == 1 and user.role == UserRole.ADMIN:
    raise LastAdminError
```

Without this function the service has no way to check if demoting this user would leave zero admins.

---

## flush + refresh pattern

All write functions use `flush()` then `refresh()`:
- `flush()` — sends INSERT/UPDATE to the DB within the open transaction; populates the `id` (via PostgreSQL RETURNING)
- `refresh()` — re-reads the row to get server-generated values (`created_at` from `server_default=func.now()`)
- No `commit()` here — the **service** commits after all its operations complete, keeping multi-repo calls atomic

---

## `create()` field defaults

Sets `is_active=True`, `is_superuser=False`, `is_verified=False` explicitly even though they have `server_default` in the DB. Avoids any ambiguity about the Python-side state before flush.

---

## Who calls this

Only `app/services/user_service.py`. No router or other service touches this repo directly.

---

## Connection check

| Import | From | Status |
|---|---|---|
| `User` | `app.db.models` | ✓ defined in Task 4 |
| `AsyncSession` | `sqlalchemy.ext.asyncio` | ✓ |
| Session injected from | `app.db.session.get_session` | ✓ Task 5 |
