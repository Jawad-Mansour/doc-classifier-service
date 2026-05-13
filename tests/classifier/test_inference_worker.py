from pathlib import Path
from typing import Any

import pytest

from app.classifier.inference.types import PredictionResult, TopKPrediction
from app.workers.inference_worker import classify_document_job


CLASS_NAMES = [
    "letter",
    "form",
    "email",
    "handwritten",
    "advertisement",
    "scientific_report",
    "scientific_publication",
    "specification",
    "file_folder",
    "news_article",
    "budget",
    "invoice",
    "presentation",
    "questionnaire",
    "resume",
    "memo",
]


class FakeBlobClient:
    def __init__(self, image_bytes: bytes) -> None:
        self.image_bytes = image_bytes
        self.download_calls: list[tuple[str, str]] = []
        self.upload_calls: list[dict[str, Any]] = []

    def download_bytes(self, bucket: str, path: str) -> bytes:
        self.download_calls.append((bucket, path))
        return self.image_bytes

    def upload_bytes(
        self,
        bucket: str,
        path: str,
        data: bytes,
        content_type: str,
    ) -> None:
        self.upload_calls.append(
            {
                "bucket": bucket,
                "path": path,
                "data": data,
                "content_type": content_type,
            }
        )


class FakePredictor:
    def __init__(self) -> None:
        self.called = False

    def predict_bytes(self, image_bytes: bytes) -> PredictionResult:
        self.called = True
        all_probs = {name: 0.0 for name in CLASS_NAMES}
        all_probs["invoice"] = 0.93
        return PredictionResult(
            label_id=11,
            label="invoice",
            confidence=0.93,
            top5=[
                TopKPrediction(label_id=11, label="invoice", confidence=0.93),
                TopKPrediction(label_id=10, label="budget", confidence=0.04),
                TopKPrediction(label_id=1, label="form", confidence=0.02),
                TopKPrediction(label_id=7, label="specification", confidence=0.005),
                TopKPrediction(label_id=15, label="memo", confidence=0.005),
            ],
            all_probs=all_probs,
            model_sha256="a" * 64,
        )


class FakePredictionService:
    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []

    async def create_prediction(self, session: object, **kwargs: Any) -> dict[str, Any]:
        self.calls.append({"session": session, **kwargs})
        return {"id": 1, **kwargs}


def _payload() -> dict[str, Any]:
    return {
        "job_id": "job-123",
        "batch_id": 12,
        "document_id": 44,
        "blob_bucket": "documents",
        "blob_path": "raw/batch_12/file1.tiff",
        "original_filename": "file1.tiff",
        "request_id": "uuid-abc-123",
    }


def test_classify_document_job_validates_required_payload_keys() -> None:
    with pytest.raises(ValueError, match="blob_path"):
        classify_document_job(
            {"job_id": "job-123"},
            blob_client=FakeBlobClient(b"unused"),
            predictor=FakePredictor(),
            prediction_service=FakePredictionService(),
            session=object(),
        )


def test_classify_document_job_runs_prediction_uploads_overlay_and_persists() -> None:
    image_path = next(iter(sorted(Path("app/classifier/eval/golden_images").glob("*.tiff"))))
    blob_client = FakeBlobClient(image_path.read_bytes())
    predictor = FakePredictor()
    prediction_service = FakePredictionService()
    session = object()

    result = classify_document_job(
        _payload(),
        blob_client=blob_client,
        predictor=predictor,
        prediction_service=prediction_service,
        session=session,
    )

    assert predictor.called
    assert blob_client.download_calls == [("documents", "raw/batch_12/file1.tiff")]
    assert len(blob_client.upload_calls) == 1
    assert blob_client.upload_calls[0]["bucket"] == "documents"
    assert blob_client.upload_calls[0]["path"] == "overlays/batch_12/44_overlay.png"
    assert blob_client.upload_calls[0]["content_type"] == "image/png"
    assert blob_client.upload_calls[0]["data"].startswith(b"\x89PNG")

    assert len(prediction_service.calls) == 1
    create_call = prediction_service.calls[0]
    assert create_call["session"] is session
    assert create_call["job_id"] == "job-123"
    assert create_call["batch_id"] == 12
    assert create_call["document_id"] == 44
    assert create_call["label_id"] == 11
    assert create_call["label"] == "invoice"
    assert create_call["confidence"] == 0.93
    assert create_call["top5"][0]["label"] == "invoice"
    assert create_call["all_probs"]["invoice"] == 0.93
    assert set(create_call["all_probs"]) == set(CLASS_NAMES)
    assert create_call["model_sha256"] == "a" * 64
    assert create_call["overlay_bucket"] == "documents"
    assert create_call["overlay_path"] == "overlays/batch_12/44_overlay.png"
    assert create_call["request_id"] == "uuid-abc-123"

    assert result == {
        "status": "success",
        "job_id": "job-123",
        "batch_id": 12,
        "document_id": 44,
        "label_id": 11,
        "label": "invoice",
        "confidence": 0.93,
        "overlay_bucket": "documents",
        "overlay_path": "overlays/batch_12/44_overlay.png",
        "model_sha256": "a" * 64,
    }
