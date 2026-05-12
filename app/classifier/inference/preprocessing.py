from io import BytesIO

import torch
import torchvision.transforms as T
from PIL import Image


IMAGE_SIZE = (224, 224)
IMAGENET_MEAN = [0.485, 0.456, 0.406]
IMAGENET_STD = [0.229, 0.224, 0.225]


def build_preprocess_transform() -> T.Compose:
    return T.Compose(
        [
            T.Resize(IMAGE_SIZE),
            T.ToTensor(),
            T.Normalize(mean=IMAGENET_MEAN, std=IMAGENET_STD),
        ]
    )


def preprocess_image_bytes(image_bytes: bytes) -> torch.Tensor:
    image = Image.open(BytesIO(image_bytes)).convert("RGB")
    tensor = build_preprocess_transform()(image)
    return tensor.unsqueeze(0)
