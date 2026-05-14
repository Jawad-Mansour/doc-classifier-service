# ruff: noqa: E402

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import torch

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from app.classifier.eval.golden import (
    build_model,
    build_transform,
    load_json,
    predict_one,
    resolve_paths,
    sha256_file,
)


def main() -> int:
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
    missing = [str(path) for path in required_paths if not path.exists()]
    if missing:
        print("Missing required paths:")
        for path in missing:
            print(f" - {path}")
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
    transform = build_transform(golden_expected["preprocessing"])

    model = build_model(num_classes=num_classes)
    model.load_state_dict(payload["model_state_dict"], strict=True)
    model.eval()

    updated_items = []
    for item in golden_expected["items"]:
        image_path = golden_images_dir / item["file"]
        pred_id, confidence, top5 = predict_one(
            model=model,
            image_path=image_path,
            transform=transform,
            class_names=class_names,
        )

        updated_item = dict(item)
        updated_item["expected_label_id"] = pred_id
        updated_item["expected_label_name"] = class_names[pred_id]
        updated_item["expected_top1_confidence"] = confidence
        updated_item["expected_top5"] = top5
        updated_items.append(updated_item)

    golden_expected["created_at_utc"] = datetime.now(timezone.utc).isoformat()
    golden_expected["items"] = updated_items

    with golden_expected_path.open("w", encoding="utf-8") as file:
        json.dump(golden_expected, file, indent=2)
        file.write("\n")

    print("Regenerated golden_expected.json for CPU replay")
    print(f"Images updated: {len(updated_items)}")
    print(f"Model SHA-256: {actual_sha}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
