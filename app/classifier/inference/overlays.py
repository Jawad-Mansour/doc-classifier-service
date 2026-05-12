from io import BytesIO

from PIL import Image, ImageDraw

from app.classifier.inference.types import PredictionResult


def create_prediction_overlay(image_bytes: bytes, prediction: PredictionResult) -> bytes:
    image = Image.open(BytesIO(image_bytes)).convert("RGB")
    draw = ImageDraw.Draw(image)

    text = f"{prediction.label} ({prediction.confidence:.2%})"
    padding = 8
    text_bbox = draw.textbbox((padding, padding), text)
    background_bbox = (
        text_bbox[0] - padding,
        text_bbox[1] - padding,
        text_bbox[2] + padding,
        text_bbox[3] + padding,
    )

    draw.rectangle(background_bbox, fill=(255, 255, 255))
    draw.text((padding, padding), text, fill=(0, 0, 0))

    output = BytesIO()
    image.save(output, format="PNG")
    return output.getvalue()
