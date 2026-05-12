from pathlib import Path

from app.classifier.inference.predictor import DocumentClassifierPredictor


def test_predictor_returns_prediction_result_for_golden_tiff() -> None:
    image_path = next(
        iter(sorted(Path("app/classifier/eval/golden_images").glob("*.tiff"))),
        None,
    )
    assert image_path is not None

    predictor = DocumentClassifierPredictor(device="cpu")
    prediction = predictor.predict_bytes(image_path.read_bytes())

    assert isinstance(prediction.label_id, int)
    assert isinstance(prediction.label, str)
    assert 0.0 <= prediction.confidence <= 1.0
    assert len(prediction.top5) == 5
    assert prediction.model_sha256
