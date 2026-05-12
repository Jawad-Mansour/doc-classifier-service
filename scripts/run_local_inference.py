import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from app.classifier.inference.overlays import create_prediction_overlay
from app.classifier.inference.predictor import DocumentClassifierPredictor


def main() -> int:
    golden_images_dir = REPO_ROOT / "app" / "classifier" / "eval" / "golden_images"
    output_path = REPO_ROOT / "tmp" / "local_inference_overlay.png"

    image_path = next(iter(sorted(golden_images_dir.glob("*.tiff"))), None)
    if image_path is None:
        raise RuntimeError(f"No golden TIFF images found in {golden_images_dir}")

    image_bytes = image_path.read_bytes()
    predictor = DocumentClassifierPredictor()
    prediction = predictor.predict_bytes(image_bytes)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(create_prediction_overlay(image_bytes, prediction))

    print(prediction.model_dump_json(indent=2))
    print(json.dumps({"image": str(image_path), "overlay": str(output_path)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
