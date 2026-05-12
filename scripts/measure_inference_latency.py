import argparse
import json
import statistics
import sys
import time
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from app.classifier.inference.predictor import DocumentClassifierPredictor


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Measure local document classifier inference latency."
    )
    parser.add_argument(
        "--images-dir",
        type=Path,
        default=Path("app/classifier/eval/golden_images"),
        help="Directory containing .tif/.tiff images.",
    )
    parser.add_argument(
        "--warmup",
        type=int,
        default=3,
        help="Number of untimed warmup passes over the image set.",
    )
    parser.add_argument(
        "--repeat",
        type=int,
        default=1,
        help="Number of measured passes over the image set.",
    )
    parser.add_argument(
        "--output-json",
        type=Path,
        default=Path("tmp/inference_latency.json"),
        help="Path for JSON latency output.",
    )
    return parser.parse_args()


def find_images(images_dir: Path) -> list[Path]:
    resolved_dir = images_dir if images_dir.is_absolute() else REPO_ROOT / images_dir
    images = sorted(
        path
        for path in resolved_dir.iterdir()
        if path.is_file() and path.suffix.lower() in {".tif", ".tiff"}
    )
    if not images:
        raise RuntimeError(f"No .tif or .tiff images found in {resolved_dir}")
    return images


def percentile(values: list[float], percentile_value: float) -> float:
    if not values:
        raise RuntimeError("Cannot compute percentile with no values.")
    sorted_values = sorted(values)
    index = round((percentile_value / 100) * (len(sorted_values) - 1))
    return sorted_values[index]


def measure_latency(
    predictor: DocumentClassifierPredictor,
    image_bytes_list: list[bytes],
    warmup: int,
    repeat: int,
) -> list[float]:
    if warmup < 0:
        raise RuntimeError("--warmup must be >= 0")
    if repeat < 1:
        raise RuntimeError("--repeat must be >= 1")

    for _ in range(warmup):
        for image_bytes in image_bytes_list:
            predictor.predict_bytes(image_bytes)

    latencies_ms = []
    for _ in range(repeat):
        for image_bytes in image_bytes_list:
            start = time.perf_counter()
            predictor.predict_bytes(image_bytes)
            elapsed = time.perf_counter() - start
            latencies_ms.append(elapsed * 1000)

    return latencies_ms


def build_results(
    image_count: int,
    total_predictions: int,
    device: str,
    latencies_ms: list[float],
) -> dict[str, Any]:
    return {
        "number_of_images": image_count,
        "total_predictions_measured": total_predictions,
        "device": device,
        "p50_ms": percentile(latencies_ms, 50),
        "p95_ms": percentile(latencies_ms, 95),
        "p99_ms": percentile(latencies_ms, 99),
        "mean_ms": statistics.fmean(latencies_ms),
        "max_ms": max(latencies_ms),
    }


def print_results(results: dict[str, Any]) -> None:
    print("Inference latency")
    print(f"Images: {results['number_of_images']}")
    print(f"Total predictions measured: {results['total_predictions_measured']}")
    print(f"Device: {results['device']}")
    print(f"p50_ms: {results['p50_ms']:.2f}")
    print(f"p95_ms: {results['p95_ms']:.2f}")
    print(f"p99_ms: {results['p99_ms']:.2f}")
    print(f"mean_ms: {results['mean_ms']:.2f}")
    print(f"max_ms: {results['max_ms']:.2f}")


def main() -> int:
    args = parse_args()
    images = find_images(args.images_dir)
    image_bytes_list = [image.read_bytes() for image in images]

    predictor = DocumentClassifierPredictor()
    latencies_ms = measure_latency(
        predictor=predictor,
        image_bytes_list=image_bytes_list,
        warmup=args.warmup,
        repeat=args.repeat,
    )

    results = build_results(
        image_count=len(images),
        total_predictions=len(latencies_ms),
        device=str(predictor.device),
        latencies_ms=latencies_ms,
    )

    output_path = args.output_json if args.output_json.is_absolute() else REPO_ROOT / args.output_json
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(results, indent=2) + "\n", encoding="utf-8")

    print_results(results)
    print(f"Saved JSON: {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
