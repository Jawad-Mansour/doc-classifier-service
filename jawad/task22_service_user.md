# Task 22 — app/services/user_service.py

## What it does

Business logic for user management. Two functions: registration and role toggling. Contains the last-admin guard that prevents locking yourself out of the system.

---

## Functions

### register_user(session, email, password) → UserDomain
Hashes the plain password via `security.hash_password()`, creates the user with `role=UserRole.AUDITOR` (default), commits, returns `UserDomain`. No audit log — registration is not a privileged action.

Operation order:
```
1. hash_password(password)
2. user_repo.create(email, hashed, role="auditor")  → flush
3. session.commit()
4. return UserDomain
```

### toggle_role(session, user_id, new_role, actor) → UserDomain

Guard: prevents demoting the last admin.

```python
if user.role == UserRole.ADMIN and new_role != UserRole.ADMIN:
    admin_count = await user_repo.count_by_role(session, UserRole.ADMIN)
    if admin_count <= 1:
        raise LastAdminError
```

Guard fires only when the user IS currently an admin AND we're moving them to a non-admin role. Promoting a non-admin to admin is always allowed.

Operation order (after guard passes):
```
1. user_repo.get_by_id()           → fetch user (also catches UserNotFound)
2. last-admin guard check
3. user_repo.update_role()         → flush
4. audit_service.log_event(actor, "role_change", "user:{id}")
5. session.commit()
6. cache_service.invalidate_user(user_id)
7. return UserDomain
```

---

## Why `count_by_role` not `count_admins`

The guard uses `count_by_role(session, UserRole.ADMIN)` — a general-purpose count by role string. This is what `user_repository.count_by_role()` provides. No special-purpose admin count function needed.

---

## Default role = auditor

`register_user` always creates new users with `UserRole.AUDITOR`. Admins are created by promoting existing users via `toggle_role`. There is no way to self-register as admin or reviewer.

---

## app/core/security.py

Written as a prerequisite for this service. Provides `hash_password()` and `verify_password()` using passlib's bcrypt context. passlib bcrypt is compatible with fastapi-users' pwdlib bcrypt — both produce and verify the same hash format, so users created via this service can also be authenticated via fastapi-users' JWT flow.

---

## Connection check

| Import | From | Status |
|---|---|---|
| `UserDomain` | `app.domain.user` | ✓ Task 8 |
| `LastAdminError`, `UserNotFound` | `app.exceptions` | ✓ Task 3 |
| `UserRole` | `app.core.constants` | ✓ Task 2 |
| `hash_password` | `app.core.security` | ✓ written alongside Task 22 |
| `user_repository` | `app.repositories.user_repository` | ✓ Task 13 |
| `audit_service` | `app.services.audit_service` | ✓ Task 18 |
| `cache_service` | `app.services.cache_service` | ✓ Task 19 |

## Who calls this

| Caller | Functions |
|---|---|
| Ali's auth router | `register_user` |
| Ali's admin router | `toggle_role` |

## Note on fastapi-users coexistence

fastapi-users 15.x manages its own registration via `UserManager.create()` which also hashes passwords. If Ali uses fastapi-users' standard `/auth/register` route, `register_user()` here may be redundant. If Ali uses a custom registration route, he calls this. The two paths use compatible bcrypt hashes so mixing them is safe.
