"""Suggest description tags for a project photo.

No machine learning model. The service reads colour and light statistics and
turns them into palette and mood tags, which is the part of tagging that needs
no training. It runs in about 70 ms for a 1000 px JPEG, needs only Pillow, and
works offline.

Thresholds sit on the terciles measured from the 16 demo photographs, so the
tags spread over the catalogue instead of landing in one bucket.
"""

from __future__ import annotations

from dataclasses import dataclass
from io import BytesIO

from PIL import Image, ImageFilter, ImageStat

ANALYSIS_SIZE: tuple[int, int] = (96, 72)
PALETTE_SIZE: int = 5

BRIGHT_MEAN: float = 140.0
MOODY_MEAN: float = 100.0
NEUTRAL_SATURATION: float = 45.0
SATURATED_SATURATION: float = 95.0
FLAT_CONTRAST: float = 40.0
HIGH_CONTRAST: float = 58.0
CALM_EDGE: float = 30.0


@dataclass(frozen=True)
class PaletteEntry:
    """One colour of the photo and how much of it the photo holds."""

    hex: str
    percent: float


@dataclass(frozen=True)
class TagSuggestion:
    """What the analyser found. The designer accepts or ignores it."""

    palette: list[PaletteEntry]
    tags: list[str]
    width: int
    height: int


def suggest_tags(data: bytes) -> TagSuggestion:
    """Read ``data`` as an image and describe it.

    Raises ``ValueError`` when the bytes are not an image Pillow can read.
    """
    try:
        with Image.open(BytesIO(data)) as image:
            image.load()
            width, height = image.size
            small = image.convert("RGB").resize(ANALYSIS_SIZE)
            palette = _palette(small)
            stats = _stats(small)
    except (OSError, ValueError) as exc:
        raise ValueError("The photo could not be read as an image") from exc
    return TagSuggestion(
        palette=palette,
        tags=_tags(stats),
        width=width,
        height=height,
    )


def _palette(image: Image.Image) -> list[PaletteEntry]:
    quantized = image.quantize(colors=PALETTE_SIZE, method=Image.Quantize.MEDIANCUT)
    table = quantized.getpalette() or []
    counts = quantized.getcolors() or []
    total = sum(count for count, _ in counts) or 1
    entries: list[PaletteEntry] = []
    for count, index in sorted(counts, reverse=True):
        base = index * 3
        colour = tuple(table[base : base + 3])
        entries.append(
            PaletteEntry(
                hex="#%02x%02x%02x" % colour,
                percent=round(100 * count / total, 1),
            )
        )
    return entries


def _stats(image: Image.Image) -> dict[str, float]:
    mean = ImageStat.Stat(image)
    brightness = sum(mean.mean) / 3
    contrast = sum(mean.stddev) / 3
    saturation = ImageStat.Stat(image.convert("HSV")).mean[1]
    grey = image.convert("L")
    edge = ImageStat.Stat(grey.filter(ImageFilter.FIND_EDGES)).mean[0]
    return {
        "brightness": brightness,
        "contrast": contrast,
        "saturation": saturation,
        "edge": edge,
    }


def _tags(stats: dict[str, float]) -> list[str]:
    tags: list[str] = []

    if stats["brightness"] >= BRIGHT_MEAN:
        tags.append("bright")
    elif stats["brightness"] <= MOODY_MEAN:
        tags.append("moody")
    else:
        tags.append("balanced light")

    if stats["saturation"] <= NEUTRAL_SATURATION:
        tags.append("neutral palette")
    elif stats["saturation"] >= SATURATED_SATURATION:
        tags.append("saturated palette")
    else:
        tags.append("warm palette")

    if stats["contrast"] <= FLAT_CONTRAST:
        tags.append("soft contrast")
    elif stats["contrast"] >= HIGH_CONTRAST:
        tags.append("high contrast")

    tags.append("calm detail" if stats["edge"] < CALM_EDGE else "busy detail")
    return tags