from pathlib import Path

from app.classifier.inference.predictor import DocumentClassifierPredictor


EXPECTED_CLASS_NAMES = {
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
}


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
    assert isinstance(prediction.all_probs, dict)
    assert len(prediction.all_probs) == 16
    assert set(prediction.all_probs) == EXPECTED_CLASS_NAMES
    assert all(isinstance(value, float) for value in prediction.all_probs.values())
    assert all(0.0 <= value <= 1.0 for value in prediction.all_probs.values())
    assert prediction.model_sha256
