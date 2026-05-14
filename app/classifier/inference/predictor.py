from collections.abc import Sequence
from pathlib import Path
from typing import Any, TypeGuard

import torch
import torch.nn as nn
from torchvision.models import convnext_tiny

from app.classifier.inference.model_validator import (
    DEFAULT_MODEL_CARD_PATH,
    DEFAULT_MODEL_PATH,
    get_class_names_from_model_card,
    validate_model_artifact,
)
from app.classifier.inference.postprocessing import logits_to_prediction
from app.classifier.inference.preprocessing import preprocess_image_bytes
from app.classifier.inference.types import PredictionResult


class DocumentClassifierPredictor:
    def __init__(
        self,
        model_path: Path = DEFAULT_MODEL_PATH,
        model_card_path: Path = DEFAULT_MODEL_CARD_PATH,
        device: str | torch.device | None = None,
    ) -> None:
        self.model_path = Path(model_path)
        self.model_card_path = Path(model_card_path)
        self.device = torch.device(device or ("cuda" if torch.cuda.is_available() else "cpu"))

        validation = validate_model_artifact(
            model_path=self.model_path,
            model_card_path=self.model_card_path,
        )
        self.model_sha256 = validation.model_sha256

        checkpoint = torch.load(self.model_path, map_location="cpu")
        self.class_names = self._resolve_class_names(checkpoint, validation.model_card)
        state_dict = self._resolve_state_dict(checkpoint)

        self.model = self._build_model(num_classes=len(self.class_names))
        self.model.load_state_dict(state_dict, strict=True)
        self.model.to(self.device)
        self.model.eval()

    def predict_bytes(self, image_bytes: bytes) -> PredictionResult:
        input_tensor = preprocess_image_bytes(image_bytes).to(self.device)
        with torch.no_grad():
            logits = self.model(input_tensor)
        return logits_to_prediction(
            logits=logits.detach().cpu(),
            class_names=self.class_names,
            model_sha256=self.model_sha256,
        )

    @staticmethod
    def _build_model(num_classes: int) -> nn.Module:
        model = convnext_tiny(weights=None)
        in_features = model.classifier[2].in_features
        model.classifier[2] = nn.Linear(in_features, num_classes)
        return model

    @staticmethod
    def _resolve_state_dict(checkpoint: Any) -> dict[str, torch.Tensor]:
        if isinstance(checkpoint, dict) and isinstance(checkpoint.get("model_state_dict"), dict):
            return checkpoint["model_state_dict"]

        if isinstance(checkpoint, dict) and checkpoint:
            if all(isinstance(value, torch.Tensor) for value in checkpoint.values()):
                return checkpoint

        raise RuntimeError("classifier.pt must contain a raw state_dict or model_state_dict.")

    @staticmethod
    def _resolve_class_names(checkpoint: Any, model_card: dict[str, Any]) -> list[str]:
        if isinstance(checkpoint, dict):
            checkpoint_class_names = checkpoint.get("class_names")
            if _is_string_sequence(checkpoint_class_names):
                return list(checkpoint_class_names)

        return get_class_names_from_model_card(model_card)


def _is_string_sequence(value: Any) -> TypeGuard[Sequence[str]]:
    return isinstance(value, Sequence) and not isinstance(value, str) and all(
        isinstance(item, str) for item in value
    )
