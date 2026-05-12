
import argparse
import hashlib
import json
import sys
from pathlib import Path

import torch
import torch.nn as nn
import torchvision.transforms as T
from PIL import Image
from torchvision.models import convnext_tiny


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def build_model(num_classes: int) -> torch.nn.Module:
    # Important:
    # weights=None avoids downloading pretrained weights in CI.
    # classifier.pt already contains the full fine-tuned state_dict.
    model = convnext_tiny(weights=None)
    in_features = model.classifier[2].in_features
    model.classifier[2] = nn.Linear(in_features, num_classes)
    return model


def load_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def build_transform(preprocessing: dict):
    return T.Compose([
        T.Resize(tuple(preprocessing["resize"])),
        T.ToTensor(),
        T.Normalize(
            mean=preprocessing["normalize_mean"],
            std=preprocessing["normalize_std"],
        ),
    ])


def resolve_paths() -> dict[str, Path]:
    eval_dir = Path(__file__).resolve().parent
    classifier_dir = eval_dir.parent
    models_dir = classifier_dir / "models"
    return {
        "eval_dir": eval_dir,
        "classifier_dir": classifier_dir,
        "models_dir": models_dir,
        "model_path": models_dir / "classifier.pt",
        "model_card_path": models_dir / "model_card.json",
        "golden_expected_path": eval_dir / "golden_expected.json",
        "golden_images_dir": eval_dir / "golden_images",
    }


@torch.inference_mode()
def predict_one(model, image_path: Path, transform, class_names):
    image = Image.open(image_path).convert("RGB")
    x = transform(image).unsqueeze(0)

    logits = model(x)
    probs = logits.softmax(dim=1)[0]

    top5_values, top5_indices = probs.topk(5)

    pred_id = int(top5_indices[0].item())
    confidence = float(top5_values[0].item())

    top5 = []
    for value, idx in zip(top5_values, top5_indices):
        label_id = int(idx.item())
        top5.append({
            "label_id": label_id,
            "label_name": class_names[label_id],
            "confidence": float(value.item()),
        })

    return pred_id, confidence, top5


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Replay golden RVL-CDIP predictions and fail if model/preprocessing changed."
    )
    parser.add_argument(
        "--tolerance",
        type=float,
        default=1e-6,
        help="Allowed absolute difference for top-1 confidence.",
    )
    args = parser.parse_args()

    paths = resolve_paths()
    model_path = paths["model_path"]
    model_card_path = paths["model_card_path"]
    golden_expected_path = paths["golden_expected_path"]
    golden_images_dir = paths["golden_images_dir"]

    required_paths = [
        model_path,
        model_card_path,
        golden_expected_path,
        golden_images_dir,
    ]

    missing = [str(p) for p in required_paths if not p.exists()]
    if missing:
        print("Missing required paths:")
        for p in missing:
            print(f" - {p}")
        return 1

    model_card = load_json(model_card_path)
    golden_expected = load_json(golden_expected_path)

    actual_sha = sha256_file(model_path)
    card_sha = model_card["artifact"]["sha256"]
    golden_sha = golden_expected["model_sha256"]

    if actual_sha != card_sha:
        print("FAILED: classifier.pt SHA-256 does not match model_card.json")
        print("Actual:", actual_sha)
        print("Card:  ", card_sha)
        return 1

    if actual_sha != golden_sha:
        print("FAILED: classifier.pt SHA-256 does not match golden_expected.json")
        print("Actual: ", actual_sha)
        print("Golden: ", golden_sha)
        return 1

    payload = torch.load(model_path, map_location="cpu")

    class_names = payload["class_names"]
    num_classes = int(payload["num_classes"])

    preprocessing = golden_expected["preprocessing"]

    transform = build_transform(preprocessing)

    model = build_model(num_classes=num_classes)
    model.load_state_dict(payload["model_state_dict"], strict=True)
    model.eval()

    failures = []

    items = golden_expected["items"]

    for item in items:
        image_path = golden_images_dir / item["file"]

        if not image_path.exists():
            failures.append({
                "file": item["file"],
                "reason": "missing_image_file",
            })
            continue

        pred_id, confidence, top5 = predict_one(
            model=model,
            image_path=image_path,
            transform=transform,
            class_names=class_names,
        )

        expected_id = int(item["expected_label_id"])
        expected_confidence = float(item["expected_top1_confidence"])

        label_ok = pred_id == expected_id
        confidence_diff = abs(confidence - expected_confidence)
        confidence_ok = confidence_diff <= args.tolerance

        if not label_ok or not confidence_ok:
            failures.append({
                "file": item["file"],
                "test_index": item.get("test_index"),
                "expected_label_id": expected_id,
                "actual_label_id": pred_id,
                "expected_confidence": expected_confidence,
                "actual_confidence": confidence,
                "confidence_diff": confidence_diff,
                "tolerance": args.tolerance,
                "actual_top5": top5,
            })

    if failures:
        print(f"FAILED: {len(failures)} / {len(items)} golden examples failed")
        print(json.dumps(failures[:10], indent=2))
        return 1

    print("PASSED: golden replay test")
    print(f"Images checked: {len(items)}")
    print(f"Model SHA-256: {actual_sha}")
    print(f"Confidence tolerance: {args.tolerance}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
