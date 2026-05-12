# Task 23 — tests/services/

## What it does

Unit tests for the business rules in the three write services. No real database, no Redis, no Docker needed — all external calls are replaced with `AsyncMock`. Tests run in milliseconds.

---

## Test files

| File | Tests | Service |
|---|---|---|
| `tests/services/test_user_service.py` | 4 | user_service |
| `tests/services/test_prediction_service.py` | 5 | prediction_service |
| `tests/services/test_batch_service.py` | 3 | batch_service |

---

## All 12 tests

| # | Test | Guard/rule verified |
|---|---|---|
| 1 | `test_toggle_role_raises_last_admin_error_when_last_admin` | `count == 1 + role == admin → LastAdminError`, no DB write |
| 2 | `test_toggle_role_raises_user_not_found` | missing user → `UserNotFound` |
| 3 | `test_toggle_role_succeeds_when_multiple_admins` | `count == 2` → no exception, role updated |
| 4 | `test_toggle_role_calls_audit_and_cache_on_success` | audit called with correct args, cache invalidated |
| 5 | `test_relabel_raises_unauthorized_when_confidence_at_threshold` | `confidence == 0.7 → UnauthorizedRelabel` (guard is `>=`) |
| 6 | `test_relabel_raises_unauthorized_when_confidence_above_threshold` | `confidence > 0.7 → UnauthorizedRelabel` |
| 7 | `test_relabel_succeeds_when_confidence_below_threshold` | `confidence < 0.7` → updates label + relabeled_by |
| 8 | `test_relabel_raises_prediction_not_found` | missing prediction → `PredictionNotFound` |
| 9 | `test_relabel_calls_audit_and_cache_on_success` | audit called with reviewer + "relabel", cache invalidated |
| 10 | `test_create_prediction_calls_audit_and_cache` | audit called with "system" + "prediction_created", cache invalidated |
| 11 | `test_update_status_raises_batch_not_found` | missing batch → `BatchNotFound` |
| 12 | `test_update_status_calls_audit_and_cache_on_success` | audit called with "system" + "status_change", cache invalidated |
| 13 | `test_add_document_returns_domain_with_populated_id` | `doc.id` is set — Aya reads this for the Redis job |

---

## Mocking strategy

All tests use `unittest.mock.patch` to replace repository and support service calls at the module level where they are used:

```python
patch("app.services.batch_service.batch_repository.update_status", return_value=fake_batch)
patch("app.services.batch_service.audit_service.log_event", new_callable=AsyncMock)
patch("app.services.batch_service.cache_service.invalidate_batch", new_callable=AsyncMock)
```

Fake ORM rows use `types.SimpleNamespace` with all fields populated to match the domain model's `from_attributes=True` expectation:
```python
fake_batch = SimpleNamespace(id=12, request_id="req", status="done", created_at=datetime(...))
```

`AsyncSession` is mocked with `AsyncMock()` — `await session.commit()` works automatically.

---

## pytest-asyncio configuration

`asyncio_mode = "auto"` added to `pyproject.toml` under `[tool.pytest.ini_options]`. This makes all `async def test_*` functions automatically run as asyncio tests without needing `@pytest.mark.asyncio` decorators. Does not affect Jad's existing sync tests.

---

## How to run

```bash
# All service tests only:
pytest tests/services/ -v

# Full test suite:
pytest -v
```

---

## What is NOT tested here

- Repositories — they are pure SQL, tested against a real DB in integration tests (not Mohamad's scope)
- Routers — Ali's responsibility
- Inference pipeline — Jad's `tests/classifier/` already covers this
- Cache namespace matching — requires a running Redis + Ali's router decorators to verify end-to-end
