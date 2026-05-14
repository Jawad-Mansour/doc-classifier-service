import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, TypeGuard


CLASSIFIER_DIR = Path(__file__).resolve().parents[1]
DEFAULT_MODEL_PATH = CLASSIFIER_DIR / "models" / "classifier.pt"
DEFAULT_MODEL_CARD_PATH = CLASSIFIER_DIR / "models" / "model_card.json"


@dataclass(frozen=True)
class ModelValidationResult:
    model_card: dict[str, Any]
    model_sha256: str


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_model_card(model_card_path: Path) -> dict[str, Any]:
    with model_card_path.open("r", encoding="utf-8") as file:
        return json.load(file)


def _find_first_string_key(data: Any, key_names: set[str]) -> str | None:
    if isinstance(data, dict):
        for key, value in data.items():
            if key in key_names and isinstance(value, str):
                return value
        for value in data.values():
            found = _find_first_string_key(value, key_names)
            if found:
                return found
    if isinstance(data, list):
        for value in data:
            found = _find_first_string_key(value, key_names)
            if found:
                return found
    return None


def get_expected_sha256(model_card: dict[str, Any]) -> str:
    sha = _find_first_string_key(
        model_card,
        {
            "sha256",
            "model_sha256",
            "artifact_sha256",
            "classifier_sha256",
        },
    )
    if not sha:
        raise RuntimeError("model_card.json does not contain a classifier SHA-256 value.")
    return sha


def get_class_names_from_model_card(model_card: dict[str, Any]) -> list[str]:
    dataset = model_card.get("dataset")
    if isinstance(dataset, dict):
        classes = dataset.get("classes")
        if _is_string_list(classes):
            return list(classes)

    for key in ("class_names", "classes", "labels"):
        value = model_card.get(key)
        if _is_string_list(value):
            return list(value)

    found = _find_first_string_list(model_card)
    if found:
        return found

    raise RuntimeError("model_card.json does not contain class names.")


def validate_model_artifact(
    model_path: Path = DEFAULT_MODEL_PATH,
    model_card_path: Path = DEFAULT_MODEL_CARD_PATH,
) -> ModelValidationResult:
    if not model_path.exists():
        raise RuntimeError(f"classifier.pt is missing: {model_path}")

    if not model_card_path.exists():
        raise RuntimeError(f"model_card.json is missing: {model_card_path}")

    model_card = load_model_card(model_card_path)
    expected_sha = get_expected_sha256(model_card)
    actual_sha = sha256_file(model_path)

    if actual_sha != expected_sha:
        raise RuntimeError(
            "classifier.pt SHA-256 mismatch: "
            f"expected {expected_sha} from model_card.json, got {actual_sha}"
        )

    return ModelValidationResult(model_card=model_card, model_sha256=actual_sha)


def _is_string_list(value: Any) -> TypeGuard[list[str]]:
    return isinstance(value, list) and bool(value) and all(isinstance(item, str) for item in value)


def _find_first_string_list(data: Any) -> list[str] | None:
    if _is_string_list(data):
        return list(data)
    if isinstance(data, dict):
        for value in data.values():
            found = _find_first_string_list(value)
            if found:
                return found
    if isinstance(data, list):
        for value in data:
            found = _find_first_string_list(value)
            if found:
                return found
    return None
