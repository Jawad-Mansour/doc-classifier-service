# Task 6 — alembic.ini + alembic/env.py + alembic/script.py.mako

## What it does

Configures Alembic — the database migration tool. After this task, running `alembic revision --autogenerate` produces a migration script by comparing our ORM models to the current DB state. The `migrate` Docker container (Aya's) runs `alembic upgrade head` on startup, which creates all 6 tables in Postgres before the API boots.

---

## alembic.ini

Standard Alembic configuration file. Key decisions:

- `script_location = alembic` — migration scripts live in the `alembic/` directory at project root
- `prepend_sys_path = .` — adds the project root to Python's sys.path so `from app.db.base import Base` works when Alembic runs
- **No `sqlalchemy.url` hardcoded here** — the URL is injected in `env.py` from the `DATABASE_SYNC_URL` environment variable. Credentials never go in config files.
- Logging configured to show Alembic INFO and suppress SQLAlchemy noise

---

## alembic/env.py

The Python script Alembic executes to connect to the DB and run migrations. Three critical decisions:

### 1. Import models before metadata

```python
from app.db import models  # noqa: F401
from app.db.base import Base
target_metadata = Base.metadata
```

This line is the most important line in the file. SQLAlchemy's `Base.metadata` only knows about a model if that model has been imported at least once. If `models.py` is not imported before `target_metadata` is set, Alembic sees empty metadata and generates an empty migration — no tables are created. The `# noqa: F401` suppresses the "imported but unused" linter warning because the import is intentional side-effect only.

### 2. Sync URL, not async URL

Alembic runs synchronously. It uses `engine_from_config` which creates a standard sync SQLAlchemy engine. This engine requires `psycopg2` (already in requirements.txt) and a `postgresql://` or `postgresql+psycopg2://` URL.

The app's `session.py` uses `DATABASE_URL` with `postgresql+asyncpg://`. Alembic uses `DATABASE_SYNC_URL` with `postgresql+psycopg2://`. These are two different env vars pointing at the same database but with different drivers.

### 3. NullPool for migrations

```python
poolclass=pool.NullPool
```

The migrate container runs once, applies migrations, then exits. Connection pooling is pointless for a one-shot process and can cause the container to hang instead of exit cleanly. `NullPool` creates a connection, uses it, and immediately closes it.

### Offline vs Online mode

- **Online mode** (normal): connects to a live DB and applies migrations directly
- **Offline mode**: generates SQL script without connecting — useful for reviewing what will be applied without running it

---

## alembic/script.py.mako

Template file that Alembic uses to generate new migration files. Was empty — filled with the standard template. Every generated migration file gets revision IDs, create date, and empty `upgrade()` / `downgrade()` function stubs that Alembic populates with the auto-detected changes.

---

## How to generate the first migration (Task 7)

After this config is in place, with `DATABASE_SYNC_URL` set:

```bash
alembic revision --autogenerate -m "initial"
alembic upgrade head
```

---

## Who depends on this

| Who | File | What they need |
|---|---|---|
| Mohamad (Task 7) | alembic/versions/ | This config must be correct before the migration can be generated |
| Aya | docker-compose.yml | `migrate` container runs `alembic upgrade head` — needs `DATABASE_SYNC_URL` env var set |
| Aya | migrate Dockerfile | Must install psycopg2-binary (already in requirements.txt) |

## Critical note for Aya

Two separate DB URL env vars are required:

| Env var | Used by | Format |
|---|---|---|
| `DATABASE_URL` | app/db/session.py (async app) | `postgresql+asyncpg://user:pass@db:5432/dbname` |
| `DATABASE_SYNC_URL` | alembic/env.py (migrations) | `postgresql+psycopg2://user:pass@db:5432/dbname` |

Both point at the same Postgres database — only the driver prefix differs. Set both in docker-compose.yml for the relevant services:
- `api` and `worker` containers need `DATABASE_URL`
- `migrate` container needs `DATABASE_SYNC_URL`
