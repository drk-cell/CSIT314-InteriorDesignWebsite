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
import re
from dataclasses import dataclass
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
    "washbasin, handbasin, washbowl, lavabo, wash-hand basin": "washbasin",
}

# The model is confident about these on photos that are not rooms: an animal
# fills the frame and no furniture is visible. Food, sport and vehicles were
# tried first and are too easy to confuse with a room, so the list is animals
# only. Measured on COCO val: 2.8% of interior photos refused, 15.8% of
# non-interior photos refused, at GATE_CONFIDENCE.
ANIMAL_PATTERN = re.compile(
    r"\b("
    r"monkey|guenon|macaque|baboon|gorilla|chimpanzee|orangutan|gibbon|siamang"
    r"|marmoset|lemur|indri|loris|tarsier"
    r"|dog|retriever|terrier|spaniel|setter|hound|shepherd|collie|poodle|mastiff"
    r"|bulldog|pug|corgi|husky|chihuahua|pinscher|griffon|keeshond|leonberg|kelpie"
    r"|cat|kitten|tabby|siamese|persian|lynx|cougar|leopard|jaguar|cheetah|panther"
    r"|lion|tiger|bear|zebra|horse|ox|sheep|ram|goat|pig|hog|elephant|camel|llama"
    r"|deer|elk|antelope|gazelle|bison|buffalo|ibex|hartebeest|impala|squirrel"
    r"|rabbit|hare|otter|skunk|badger|weasel|mink|polecat|armadillo|sloth|panda"
    r"|dugong|whale|dolphin|walrus"
    r"|bird|parrot|macaw|cockatoo|lorikeet|eagle|hawk|vulture|owl|penguin|ostrich"
    r"|peacock|flamingo|stork|heron|crane|swan|goose|duck|quail|partridge"
    r"|fish|shark|stingray|eel|salmon|trout|goldfish|tench|sturgeon|puffer"
    r"|snake|serpent|lizard|gecko|iguana|chameleon|crocodile|alligator"
    r"|frog|toad|salamander|newt|spider|tarantula|scorpion|butterfly|moth|beetle"
    r"|grasshopper|cricket|mantis|dragonfly"
    r")\b",
    re.IGNORECASE,
)

# How sure the model must be before the gate overrules a photo.
GATE_CONFIDENCE: float = 0.25


def is_animal(label: str) -> bool:
    """Return True when the label names an animal.

    Only the first synonym is matched, so "potted plant" cannot trip on "ant",
    and the word boundaries keep "car" away from "cardoon".
    """
    primary = label.split(",")[0].strip()
    return bool(ANIMAL_PATTERN.search(primary))


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


@dataclass(frozen=True)
class Reading:
    """What one inference pass saw. The diagnostics drive the interior gate."""

    tags: list[str]
    top_label: str
    top_probability: float
    interior_probability: float
    subject: str


def read(data: bytes) -> Reading | None:
    """Run one inference pass and return the tags plus the diagnostics.

    ``None`` means the model is absent or the bytes are not readable. Callers
    must fall back to the colour stage, not fail.
    ``interior_probability`` is the best probability among the classes that map
    to a catalogue tag. A photo of a monkey scores near zero there even when the
    model is confident about the monkey.
    """
    loaded = _session()
    if loaded is None:
        return None
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
        return None

    interior = 0.0
    tags: list[str] = []
    order = probs.argsort()[::-1][:50]
    for index in order:
        label = labels[index] if index < len(labels) else ""
        tag = LABEL_TO_TAG.get(label)
        probability = float(probs[index])
        if tag is not None:
            interior = max(interior, probability)
            if probability >= FLOOR and len(tags) < LIMIT and tag not in tags:
                tags.append(tag)
    best = int(order[0])
    best_label = labels[best] if best < len(labels) else ""
    subject = "room"
    if (
        not tags
        and interior < FLOOR
        and float(probs[best]) >= GATE_CONFIDENCE
        and is_animal(best_label)
    ):
        subject = "other"
    return Reading(
        tags=tags,
        top_label=best_label,
        top_probability=float(probs[best]),
        interior_probability=interior,
        subject=subject,
    )


def object_tags(data: bytes) -> list[str]:
    """Return up to ``LIMIT`` catalogue tags for ``data``, most confident first.

    An empty list means the model is absent, refused the bytes, or saw nothing
    it can name. The caller must treat that as "colour tags only".
    """
    reading = read(data)
    return [] if reading is None else reading.tags


def engine_name() -> str:
    """Name the analyser for the response, so the screen can be honest."""
    return "objects and colour" if available() else "colour only"
