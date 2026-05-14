from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

from app.exceptions import PredictionNotFound, UnauthorizedRelabel
from app.services import prediction_service


def _fake_prediction(confidence: float = 0.93, prediction_id: int = 1) -> SimpleNamespace:
    return SimpleNamespace(
        id=prediction_id,
        job_id="job-abc",
        batch_id=1,
        document_id=1,
        label_id=11,
        label="invoice",
        confidence=confidence,
        top5=[{"label_id": 11, "label": "invoice", "confidence": confidence}],
        all_probs={"invoice": confidence, "budget": 0.04},
        model_sha256="a" * 64,
        overlay_bucket="docs",
        overlay_path="overlays/1.png",
        relabeled_by=None,
        request_id="req-001",
        created_at=datetime(2024, 1, 1, tzinfo=timezone.utc),
    )


# ── Test 5 ─────────────────────────────────────────────────────────────────────
async def test_relabel_raises_unauthorized_when_confidence_at_threshold():
    """Confidence exactly at 0.7 must be rejected — the guard is >=."""
    session = AsyncMock()

    with patch(
        "app.services.prediction_service.prediction_repository.get_by_id",
        return_value=_fake_prediction(confidence=0.7),
    ):
        with pytest.raises(UnauthorizedRelabel):
            await prediction_service.relabel(
                session, 1, "budget", "reviewer@example.com", "reviewer"
            )


async def test_relabel_raises_unauthorized_when_confidence_above_threshold():
    """Confidence above 0.7 must also be rejected."""
    session = AsyncMock()

    with patch(
        "app.services.prediction_service.prediction_repository.get_by_id",
        return_value=_fake_prediction(confidence=0.95),
    ):
        with pytest.raises(UnauthorizedRelabel):
            await prediction_service.relabel(
                session, 1, "budget", "reviewer@example.com", "reviewer"
            )


async def test_admin_can_relabel_high_confidence_prediction():
    """Admin relabeling should bypass the reviewer-only confidence restriction."""
    session = AsyncMock()
    original = _fake_prediction(confidence=0.95, prediction_id=9)
    relabeled = SimpleNamespace(**vars(original))
    relabeled.label_id = 10
    relabeled.label = "budget"
    relabeled.relabeled_by = "admin@example.com"

    with (
        patch("app.services.prediction_service.prediction_repository.get_by_id", return_value=original),
        patch("app.services.prediction_service.prediction_repository.update_label", return_value=relabeled),
        patch("app.services.prediction_service.audit_service.log_event", new_callable=AsyncMock),
        patch("app.services.prediction_service.cache_service.invalidate_prediction_write", new_callable=AsyncMock),
    ):
        result = await prediction_service.relabel(
            session, 9, "budget", "admin@example.com", "admin"
        )

    assert result.label == "budget"
    assert result.relabeled_by == "admin@example.com"


# ── Test 6 ─────────────────────────────────────────────────────────────────────
async def test_relabel_succeeds_when_confidence_below_threshold():
    """Confidence below 0.7 must allow relabeling and return updated PredictionDomain."""
    session = AsyncMock()
    original = _fake_prediction(confidence=0.45, prediction_id=7)
    relabeled = SimpleNamespace(**vars(original))
    relabeled.label_id = 10
    relabeled.label = "budget"
    relabeled.relabeled_by = "reviewer@example.com"

    with (
        patch("app.services.prediction_service.prediction_repository.get_by_id", return_value=original),
        patch("app.services.prediction_service.prediction_repository.update_label", return_value=relabeled),
        patch("app.services.prediction_service.audit_service.log_event", new_callable=AsyncMock),
        patch("app.services.prediction_service.cache_service.invalidate_prediction_write", new_callable=AsyncMock),
    ):
        result = await prediction_service.relabel(
            session, 7, "budget", "reviewer@example.com", "reviewer"
        )

    assert result.label == "budget"
    assert result.relabeled_by == "reviewer@example.com"


# ── Test 7 ─────────────────────────────────────────────────────────────────────
async def test_relabel_raises_prediction_not_found():
    """Non-existent prediction_id must raise PredictionNotFound."""
    session = AsyncMock()

    with patch(
        "app.services.prediction_service.prediction_repository.get_by_id",
        return_value=None,
    ):
        with pytest.raises(PredictionNotFound):
            await prediction_service.relabel(
                session, 999, "budget", "reviewer@example.com", "reviewer"
            )


# ── Test 8 ─────────────────────────────────────────────────────────────────────
async def test_relabel_calls_audit_and_cache_on_success():
    """Successful relabel must log an audit event and invalidate predictions cache."""
    session = AsyncMock()
    original = _fake_prediction(confidence=0.3, prediction_id=10)
    relabeled = SimpleNamespace(**vars(original))
    relabeled.label = "budget"
    relabeled.label_id = 10

    with (
        patch("app.services.prediction_service.prediction_repository.get_by_id", return_value=original),
        patch("app.services.prediction_service.prediction_repository.update_label", return_value=relabeled),
        patch("app.services.prediction_service.audit_service.log_event", new_callable=AsyncMock) as mock_audit,
        patch("app.services.prediction_service.cache_service.invalidate_prediction_write", new_callable=AsyncMock) as mock_cache,
    ):
        await prediction_service.relabel(
            session, 10, "budget", "reviewer@example.com", "reviewer"
        )

    mock_audit.assert_called_once_with(session, "reviewer@example.com", "relabel", "prediction:10")
    mock_cache.assert_called_once_with(1)


# ── Test 9 ─────────────────────────────────────────────────────────────────────
async def test_create_prediction_calls_audit_and_cache():
    """create_prediction must log an audit event and invalidate predictions cache after saving."""
    session = AsyncMock()
    saved = _fake_prediction(confidence=0.91, prediction_id=55)

    with (
        patch("app.services.prediction_service.prediction_repository.create", return_value=saved),
        patch("app.services.prediction_service.audit_service.log_event", new_callable=AsyncMock) as mock_audit,
        patch("app.services.prediction_service.cache_service.invalidate_prediction_write", new_callable=AsyncMock) as mock_cache,
    ):
        result = await prediction_service.create_prediction(
            session,
            job_id="job-abc",
            batch_id=1,
            document_id=1,
            label_id=11,
            label="invoice",
            confidence=0.91,
            top5=[],
            all_probs={"invoice": 0.91},
            model_sha256="a" * 64,
            overlay_bucket="docs",
            overlay_path="overlays/1.png",
            request_id="req-001",
        )

    assert result.id == 55
    mock_audit.assert_called_once_with(session, "system", "prediction_created", "document:1")
    mock_cache.assert_called_once_with(1)
