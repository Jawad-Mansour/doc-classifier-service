from app.classifier.inference.model_validator import (
    DEFAULT_MODEL_CARD_PATH,
    DEFAULT_MODEL_PATH,
    validate_model_artifact,
)


def test_classifier_sha_matches_model_card() -> None:
    validation = validate_model_artifact(
        model_path=DEFAULT_MODEL_PATH,
        model_card_path=DEFAULT_MODEL_CARD_PATH,
    )

    assert validation.model_sha256
    assert validation.model_card["artifact"]["sha256"] == validation.model_sha256
