# Task 1 — app/db/base.py

## What it does

Defines the single SQLAlchemy declarative base class that every ORM model in the project inherits from. It also carries the `metadata` object that Alembic reads when auto-generating migrations.

## Code

```python
from sqlalchemy.orm import DeclarativeBase

class Base(DeclarativeBase):
    pass
```

## Approach and defense

SQLAlchemy 2.x (confirmed in pyproject.toml: `sqlalchemy>=2.0.0`) uses `DeclarativeBase` as the recommended base class. The old `declarative_base()` factory from 1.x still works but is legacy. Using `DeclarativeBase` gives full type-checking support and is the correct style for this project.

No columns, no mixins, no timestamps added here. Adding shared columns to a base class is an over-engineering trap — not every table needs the same fields, and the project spec does not require it.

## Who depends on this

| Who | File | How they use it |
|---|---|---|
| Mohamad (Task 4) | app/db/models.py | All 6 ORM models inherit from `Base` |
| Mohamad (Task 6) | alembic/env.py | Imports `Base.metadata` so Alembic can detect all models and auto-generate migrations |

## Notes

- `app/db/models.py` must import `Base` from this file — not redefine it elsewhere
- `alembic/env.py` must import `Base` from this file — if it imports from models.py directly, circular imports will occur
- No other file in the project needs to import from `base.py` directly
