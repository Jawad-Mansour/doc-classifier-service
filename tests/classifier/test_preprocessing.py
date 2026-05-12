from pathlib import Path

from app.classifier.inference.preprocessing import preprocess_image_bytes


def test_preprocess_golden_tiff_shape() -> None:
    image_path = next(
        iter(sorted(Path("app/classifier/eval/golden_images").glob("*.tiff"))),
        None,
    )
    assert image_path is not None

    tensor = preprocess_image_bytes(image_path.read_bytes())

    assert list(tensor.shape) == [1, 3, 224, 224]
