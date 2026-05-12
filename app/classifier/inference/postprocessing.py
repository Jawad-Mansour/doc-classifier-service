from collections.abc import Sequence

import torch

from app.classifier.inference.types import PredictionResult, TopKPrediction


def logits_to_prediction(
    logits: torch.Tensor,
    class_names: Sequence[str],
    model_sha256: str,
) -> PredictionResult:
    if logits.ndim == 2:
        if logits.shape[0] != 1:
            raise RuntimeError("Expected logits for a single image.")
        logits = logits[0]

    if logits.ndim != 1:
        raise RuntimeError("Expected logits with shape [num_classes] or [1, num_classes].")

    if len(class_names) < 5:
        raise RuntimeError("At least 5 class names are required for top5 predictions.")

    if logits.shape[0] != len(class_names):
        raise RuntimeError(
            f"Logits class count ({logits.shape[0]}) does not match class names ({len(class_names)})."
        )

    probabilities = torch.softmax(logits, dim=0)
    all_probs = {
        class_name: float(probability.item())
        for class_name, probability in zip(class_names, probabilities)
    }
    top5_values, top5_indices = probabilities.topk(5)

    top5 = [
        TopKPrediction(
            label_id=int(index.item()),
            label=class_names[int(index.item())],
            confidence=float(value.item()),
        )
        for value, index in zip(top5_values, top5_indices)
    ]

    top1 = top5[0]
    return PredictionResult(
        label_id=top1.label_id,
        label=top1.label,
        confidence=float(top1.confidence),
        top5=top5,
        all_probs=all_probs,
        model_sha256=model_sha256,
    )
