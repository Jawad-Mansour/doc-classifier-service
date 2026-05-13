# Aya

## Scope
- Infra, Docker, Redis, MinIO, SFTP, Vault, CI

## Completed
- CI installs dependencies from `requirements.txt`.
- Added missing CI/runtime dependencies needed by infra/app imports.
- Added local default app/database settings so smoke tests can import app config without external env.

## Files changed
- `requirements.txt`
- `app/core/config.py`

## How to test
```bash
.venv/bin/pip install -r requirements.txt
.venv/bin/python -m pytest tests/smoke
.venv/bin/python - <<'PY'
from app.core.config import settings
print("DATABASE_URL:", settings.DATABASE_URL)
from app.main import app
print("app import OK")
PY
```

## Blocked
- Smoke tests are now blocked by an API schema export issue, not by the previous missing dependency/config errors.
- Current error: `ImportError: cannot import name 'HealthResponse' from 'app.api.schemas'`.
- `app/api/routers/health.py` imports `HealthResponse`, but `app/api/schemas/__init__.py` is empty.

## Contracts needed
- Pending update

## Caveats / known limitations
- Pending update

## Next steps
- Pending update
