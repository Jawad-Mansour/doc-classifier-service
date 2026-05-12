from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

from app.exceptions import BatchNotFound
from app.services import batch_service


def _fake_batch(batch_id: int = 1, status: str = "pending") -> SimpleNamespace:
    return SimpleNamespace(
        id=batch_id,
        request_id="req-001",
        status=status,
        created_at=datetime(2024, 1, 1, tzinfo=timezone.utc),
    )


def _fake_document(doc_id: int = 44) -> SimpleNamespace:
    return SimpleNamespace(
        id=doc_id,
        batch_id=1,
        filename="invoice.tiff",
        blob_bucket="documents",
        blob_path="raw/batch_1/invoice.tiff",
        created_at=datetime(2024, 1, 1, tzinfo=timezone.utc),
    )


# ── Test 10 ────────────────────────────────────────────────────────────────────
async def test_update_status_raises_batch_not_found():
    """update_status must raise BatchNotFound when the batch_id doesn't exist."""
    session = AsyncMock()

    with patch(
        "app.services.batch_service.batch_repository.update_status",
        return_value=None,
    ):
        with pytest.raises(BatchNotFound):
            await batch_service.update_status(session, 999, "done")


# ── Test 11 ────────────────────────────────────────────────────────────────────
async def test_update_status_calls_audit_and_cache_on_success():
    """Successful status update must log an audit event and invalidate the batch cache."""
    session = AsyncMock()
    updated_batch = _fake_batch(batch_id=12, status="done")

    with (
        patch("app.services.batch_service.batch_repository.update_status", return_value=updated_batch),
        patch("app.services.batch_service.audit_service.log_event", new_callable=AsyncMock) as mock_audit,
        patch("app.services.batch_service.cache_service.invalidate_batch", new_callable=AsyncMock) as mock_cache,
    ):
        result = await batch_service.update_status(session, 12, "done")

    assert result.status == "done"
    mock_audit.assert_called_once_with(session, "system", "status_change", "batch:12")
    mock_cache.assert_called_once_with(12)


# ── Test 12 ────────────────────────────────────────────────────────────────────
async def test_add_document_returns_domain_with_populated_id():
    """add_document must return a DocumentDomain whose id is set — Aya depends on this."""
    session = AsyncMock()
    saved_doc = _fake_document(doc_id=44)

    with patch(
        "app.services.batch_service.document_repository.create",
        return_value=saved_doc,
    ):
        result = await batch_service.add_document(
            session,
            batch_id=1,
            filename="invoice.tiff",
            blob_bucket="documents",
            blob_path="raw/batch_1/invoice.tiff",
        )

    assert result.id == 44
    assert result.batch_id == 1
    assert result.filename == "invoice.tiff"
