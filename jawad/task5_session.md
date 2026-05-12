# Task 5 — app/db/session.py

## What it does

Creates the async SQLAlchemy engine and session factory. Every repository function receives an `AsyncSession` from here. The `get_session` async generator is also used as a FastAPI dependency — Ali's route handlers inject it via `Depends(get_session)` to pass sessions down to services and repositories.

## Code

```python
import os
from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

DATABASE_URL = os.environ["DATABASE_URL"]

engine = create_async_engine(DATABASE_URL, echo=False)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

async def get_session() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        yield session
```

## Approach and defense

### Why async?

`fastapi-users-db-sqlalchemy==7.0.0` (confirmed in requirements.txt) requires async SQLAlchemy. FastAPI itself is async. Running sync DB calls in an async framework blocks the event loop and kills concurrency under load. The project spec also explicitly lists "Async DB session" as a Mohamad responsibility.

### Why `asyncpg` and not `psycopg2`?

`psycopg2-binary` (in requirements.txt) is a **synchronous** driver — it cannot drive async SQLAlchemy. Async SQLAlchemy requires an async-compatible driver. `asyncpg` is the standard choice for PostgreSQL with async SQLAlchemy.

**Action required for Aya:** Add `asyncpg` to `pyproject.toml` dependencies and regenerate `requirements.txt`. The `DATABASE_URL` environment variable must use the `postgresql+asyncpg://` scheme, not `postgresql://`.

Example:
```
DATABASE_URL=postgresql+asyncpg://user:password@db:5432/docclassifier
```

### Why `expire_on_commit=False`?

By default, after `session.commit()`, SQLAlchemy marks every loaded object's attributes as expired. The next time you access any attribute (e.g. `batch.id` after saving a new batch), SQLAlchemy tries to reload it from the database. But at that point the session context has already closed, causing a `DetachedInstanceError` or `MissingGreenlet` error.

Setting `expire_on_commit=False` keeps the object's attributes alive after commit. This is essential for the pattern our repositories use: insert a row, commit, then return the ORM object to the service layer which converts it to a domain model.

### Why `echo=False`?

`echo=True` would print every SQL statement to stdout. Aya's structured JSON logger handles observability — mixing raw SQL into stdout would pollute structured logs. If needed for debugging, this can be toggled via an env var later.

### Why read `DATABASE_URL` from `os.environ` directly?

Aya owns `app/core/config.py` but it is currently empty. Reading directly from `os.environ` is the minimal correct approach right now. When Aya writes `config.py`, this line should be updated to:

```python
from app.core.config import settings
DATABASE_URL = settings.database_url
```

The env var name `DATABASE_URL` must be agreed with Aya so her `docker-compose.yml` and `.env.example` use the same name.

### Why a generator (`yield`) and not a context manager?

Using `yield` inside `get_session` makes it a FastAPI dependency that:
1. Opens a session before the route handler runs
2. Passes the session to the handler
3. Automatically closes it after the response is sent (even on exceptions)

This is the standard FastAPI + SQLAlchemy async pattern. The `async with AsyncSessionLocal() as session` block guarantees the session is always closed — no connection leaks.

## Who depends on this

| Who | File | How they use it |
|---|---|---|
| Mohamad (Tasks 13–17) | repositories/ | All repository functions take `session: AsyncSession` as first argument — session comes from here |
| Ali | app/api/deps/auth.py | Injects `get_session` via `Depends(get_session)` to pass sessions into route handlers |
| Mohamad (Task 6) | alembic/env.py | Uses a **sync** version of the DB URL — NOT this async engine. Alembic runs synchronously with psycopg2 |

## Critical note for Aya

Two actions required:

1. **Add `asyncpg` to `pyproject.toml`** and regenerate `requirements.txt`:
   ```toml
   "asyncpg>=0.29.0",
   ```

2. **Set `DATABASE_URL` in `docker-compose.yml`** with `postgresql+asyncpg://` scheme for the `api` and `worker` services:
   ```yaml
   DATABASE_URL: postgresql+asyncpg://postgres:postgres@db:5432/docclassifier
   ```

   And a separate sync URL for the `migrate` container (Alembic uses psycopg2):
   ```yaml
   DATABASE_URL: postgresql://postgres:postgres@db:5432/docclassifier
   ```

## Critical note for Task 6 (Alembic)

`alembic/env.py` must **not** use this async engine. Alembic runs synchronously. It should use a separate sync connection with `psycopg2-binary` (already in requirements.txt):
```
postgresql+psycopg2://user:password@host:port/dbname
```
or simply:
```
postgresql://user:password@host:port/dbname
```
This means two different DATABASE_URL values — one for the app (asyncpg), one for migrations (psycopg2). Aya should expose both as separate env vars, e.g. `DATABASE_URL` and `DATABASE_SYNC_URL`.
