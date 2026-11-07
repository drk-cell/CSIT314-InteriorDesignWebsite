"""Read furniture and fixture names from a photo with a small ONNX model.

MobileNetV2, 14 MB, trained on ImageNet. Only thirty of its 1000 classes mean
something to an interior design catalogue, so every label goes through
``LABEL_TO_TAG``. A confident label that maps to nothing is dropped, which is
why a wrong guess cannot reach the user as a tag.

The model is optional on purpose. Without ``backend/models/mobilenetv2-7.onnx``
or without onnxruntime, ``object_tags`` returns an empty list and the colour
tags from ``tag_suggestion_service`` still answer. The feature degrades; it does
not fail.

This module is the only place that knows about the model, so replacing it with a
better one touches one file.
"""

from __future__ import annotations

import os
from functools import lru_cache
from io import BytesIO
from pathlib import Path

MODEL_PATH = Path(
    os.environ.get(
        "APP_TAG_MODEL",
        Path(__file__).resolve().parents[2] / "models" / "mobilenetv2-7.onnx",
    )
)

# Input the model expects: 224 square, RGB, ImageNet normalisation.
SIZE = (224, 224)
MEAN = (0.485, 0.456, 0.406)
STD = (0.229, 0.224, 0.225)
FLOOR = 0.05
LIMIT = 3

# ImageNet label (as written in synset.txt, after the n-code) -> catalogue tag.
# Labels that are not here are noise for this project: "throne", "vault",
# "groom" and "photocopier" all appear on interior photographs.
LABEL_TO_TAG: dict[str, str] = {
    "studio couch, day bed": "sofa",
    "dining table, board": "dining table",
    "desk": "desk",
    "bookcase": "bookshelf",
    "china cabinet, china closet": "display cabinet",
    "wardrobe, closet, press": "wardrobe",
    "chest": "chest of drawers",
    "dresser": "chest of drawers",
    "file, file cabinet, filing cabinet": "filing cabinet",
    "four-poster": "bed",
    "quilt, comforter, comfort, puff": "bedding",
    "crib, cot": "cot",
    "cradle": "cot",
    "sliding door": "sliding door",
    "window shade": "window shade",
    "window screen": "window screen",
    "shower curtain": "shower curtain",
    "theater curtain, theatre curtain": "curtain",
    "lampshade, lamp shade": "lamp",
    "table lamp": "lamp",
    "wall clock": "wall clock",
    "analog clock": "clock",
    "digital clock": "clock",
    "dishwasher, dish washer, dishwashing machine": "dishwasher",
    "microwave, microwave oven": "microwave",
    "refrigerator, icebox": "refrigerator",
    "stove": "stove",
    "toaster": "toaster",
    "plate rack": "open shelving",
    "bathtub, bathing tub, bath, tub": "bathtub",
    "toilet seat": "toilet",
    "medicine chest, medicine cabinet": "medicine cabinet",
    "vase": "vase",
    "pot, flowerpot": "plant pot",
    "candle, taper, wax light": "candle",
    "doormat, welcome mat": "doormat",
    "prayer rug, prayer mat": "rug",
    "park bench": "bench",
    "rocking chair, rocker": "chair",
    "folding chair": "chair",
    "barber chair": "chair",
    "pool table, billiard table, snooker table": "pool table",
    "fire screen, fireguard": "fireplace",
    "shoji": "paper screen",
    "patio, terrace": "terrace",
}


@lru_cache(maxsize=1)
def _session():
    """Load the model once. Return None when the model or runtime is absent."""
    if not MODEL_PATH.is_file():
        return None
    labels_file = MODEL_PATH.with_name("synset.txt")
    if not labels_file.is_file():
        return None
    try:
        import onnxruntime as ort
        from PIL import Image  # noqa: F401  - proves Pillow is present
    except ImportError:
        return None
    session = ort.InferenceSession(
        str(MODEL_PATH), providers=["CPUExecutionProvider"]
    )
    labels = [
        line.split(" ", 1)[1] if " " in line else line
        for line in labels_file.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    return session, labels


def available() -> bool:
    """Return True when a model can answer."""
    return _session() is not None


def object_tags(data: bytes) -> list[str]:
    """Return up to ``LIMIT`` catalogue tags for ``data``, most confident first.

    An empty list means the model is absent, refused the bytes, or saw nothing
    it can name. The caller must treat that as "colour tags only".
    """
    loaded = _session()
    if loaded is None:
        return []
    session, labels = loaded
    try:
        import numpy as np
        from PIL import Image

        with Image.open(BytesIO(data)) as image:
            image.load()
            small = image.convert("RGB").resize(SIZE)
            array = np.asarray(small, dtype=np.float32) / 255.0
        array = (array - np.asarray(MEAN, dtype=np.float32)) / np.asarray(
            STD, dtype=np.float32
        )
        batch = array.transpose(2, 0, 1)[None, ...]
        name = session.get_inputs()[0].name
        logits = session.run(None, {name: batch})[0][0]
        shifted = np.exp(logits - logits.max())
        probs = shifted / shifted.sum()
    except (OSError, ValueError, RuntimeError):
        return []

    order = probs.argsort()[::-1][:50]
    tags: list[str] = []
    for index in order:
        if probs[index] < FLOOR:
            break
        label = labels[index] if index < len(labels) else ""
        tag = LABEL_TO_TAG.get(label)
        if tag and tag not in tags:
            tags.append(tag)
        if len(tags) >= LIMIT:
            break
    return tags


def engine_name() -> str:
    """Name the analyser for the response, so the screen can be honest."""
    return "objects and colour" if available() else "colour only"
