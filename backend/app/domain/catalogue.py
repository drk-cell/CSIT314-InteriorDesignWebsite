"""The fixed catalogue: the rooms and styles the platform offers.

The screens build their dropdowns from these lists, so the platform has one
vocabulary. A project stores the label as text, and the search compares text.
"""

from __future__ import annotations

CATEGORIES: tuple[str, ...] = (
    "Living Room",
    "Bedroom",
    "Kitchen",
    "Dining Room",
    "Home Office",
    "Bathroom",
    "Children's Room",
    "Balcony",
    "Studio",
    "Whole Home",
)

STYLES: tuple[str, ...] = (
    "Minimal",
    "Scandinavian",
    "Contemporary",
    "Traditional",
    "Japandi",
    "Industrial",
    "Eclectic",
)

BUDGET_MIN: int = 0
BUDGET_MAX: int = 200_000
BUDGET_STEP: int = 5_000