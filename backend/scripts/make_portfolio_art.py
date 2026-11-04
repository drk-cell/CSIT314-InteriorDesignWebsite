"""Generate the placeholder portfolio artwork for the demo.

Every image is a flat illustration of one room: wall, floor, a window, a rug,
one piece of furniture, and a plant or a lamp. Standard library only, and the
same run always produces the same files.

Run from the backend folder:

    .venv/Scripts/python.exe scripts/make_portfolio_art.py
"""

from __future__ import annotations

import json
from pathlib import Path

WIDTH = 800
HEIGHT = 600
FLOOR_LINE = 470
COUNT = 24

OUTPUT = Path(__file__).resolve().parents[2] / "frontend" / "public" / "portfolio"

PALETTES: list[dict[str, str]] = [
    {
        "name": "sand",
        "wall": "#efe7dc",
        "floor": "#cbb79b",
        "wood": "#9c7b52",
        "textile": "#d9c7ae",
        "accent": "#7d6a52",
        "sky": "#cfe0e8",
    },
    {
        "name": "sage",
        "wall": "#e6ebe2",
        "floor": "#b9c1a6",
        "wood": "#8b7a5e",
        "textile": "#cfd8c2",
        "accent": "#5f7059",
        "sky": "#d7e5ea",
    },
    {
        "name": "terracotta",
        "wall": "#f2e3d9",
        "floor": "#c98f6f",
        "wood": "#8d5b3f",
        "textile": "#e3bda6",
        "accent": "#a2543a",
        "sky": "#dbe7ec",
    },
    {
        "name": "slate",
        "wall": "#e4e7ea",
        "floor": "#8d949b",
        "wood": "#5f676e",
        "textile": "#c3c9cf",
        "accent": "#3f474d",
        "sky": "#cfdde5",
    },
    {
        "name": "cream",
        "wall": "#f7f3ea",
        "floor": "#d8cbb2",
        "wood": "#a3895f",
        "textile": "#eee4d2",
        "accent": "#6f6650",
        "sky": "#d6e4ea",
    },
    {
        "name": "olive",
        "wall": "#ece9d8",
        "floor": "#a9a07a",
        "wood": "#7a7150",
        "textile": "#d6d1b4",
        "accent": "#575531",
        "sky": "#d3e2e4",
    },
]

STYLES = ["Minimal", "Scandinavian", "Industrial", "Japandi", "Contemporary", "Traditional"]
ROOMS = [
    "Living Room",
    "Bedroom",
    "Kitchen",
    "Studio",
    "Dining Room",
    "Home Office",
    "Bathroom",
    "Balcony",
]

WINDOW_X = {"left": 60, "centre": 300, "right": 520}


def rect(x: int, y: int, w: int, h: int, fill: str, extra: str = "") -> str:
    return f'<rect x="{x}" y="{y}" width="{w}" height="{h}" fill="{fill}"{extra}/>'


def window(x: int, palette: dict[str, str]) -> str:
    """A three pane window with a sill."""
    frame = palette["accent"]
    parts = [
        rect(x - 8, 60, 236, 8, frame),
        rect(x, 68, 220, 300, frame),
        rect(x + 6, 74, 208, 288, palette["sky"]),
        rect(x + 6, 210, 208, 6, frame),
        rect(x + 106, 74, 8, 288, frame),
        rect(x - 14, 368, 248, 10, frame),
    ]
    return "".join(parts)


def rug(shape: str, palette: dict[str, str]) -> str:
    if shape == "ellipse":
        return (
            f'<ellipse cx="400" cy="530" rx="260" ry="44" '
            f'fill="{palette["textile"]}"/>'
        )
    return rect(150, 492, 500, 76, palette["textile"], ' rx="10"')


def sofa(x: int, palette: dict[str, str]) -> str:
    wood = palette["wood"]
    return "".join(
        [
            rect(x, 330, 250, 40, wood, ' rx="6"'),
            rect(x, 360, 250, 90, palette["accent"], ' rx="8"'),
            rect(x + 16, 372, 100, 46, palette["textile"], ' rx="6"'),
            rect(x + 132, 372, 100, 46, palette["textile"], ' rx="6"'),
            rect(x + 12, 450, 18, 24, wood),
            rect(x + 220, 450, 18, 24, wood),
        ]
    )


def table(x: int, palette: dict[str, str]) -> str:
    wood = palette["wood"]
    return "".join(
        [
            rect(x, 382, 220, 18, wood, ' rx="4"'),
            rect(x + 22, 400, 14, 72, wood),
            rect(x + 184, 400, 14, 72, wood),
            rect(x + 70, 330, 60, 52, palette["accent"], ' rx="4"'),
        ]
    )


def shelf(x: int, palette: dict[str, str]) -> str:
    wood = palette["wood"]
    parts = [rect(x, 210, 200, 10, wood), rect(x, 290, 200, 10, wood), rect(x, 370, 200, 10, wood)]
    parts += [rect(x, 210, 10, 170, wood), rect(x + 190, 210, 10, 170, wood)]
    for offset, colour in ((34, palette["accent"]), (58, palette["textile"])):
        parts.append(rect(x + offset, 220, 18, 68, colour))
    parts.append(rect(x + 120, 300, 22, 68, palette["textile"]))
    parts.append(rect(x + 150, 316, 16, 52, palette["accent"]))
    return "".join(parts)


def bed(x: int, palette: dict[str, str]) -> str:
    wood = palette["wood"]
    return "".join(
        [
            rect(x, 250, 260, 60, wood, ' rx="6"'),
            rect(x, 300, 260, 120, palette["textile"], ' rx="8"'),
            rect(x + 20, 318, 90, 44, "#ffffff", ' rx="8" opacity="0.75"'),
            rect(x + 130, 318, 90, 44, "#ffffff", ' rx="8" opacity="0.75"'),
            rect(x, 420, 260, 26, palette["accent"], ' rx="4"'),
        ]
    )


def plant(x: int, palette: dict[str, str]) -> str:
    leaf = palette["accent"]
    return "".join(
        [
            rect(x, 420, 56, 48, palette["wood"], ' rx="6"'),
            f'<ellipse cx="{x + 28}" cy="392" rx="26" ry="34" fill="{leaf}"/>',
            f'<ellipse cx="{x + 8}" cy="404" rx="16" ry="24" fill="{leaf}" opacity="0.8"/>',
            f'<ellipse cx="{x + 48}" cy="404" rx="16" ry="24" fill="{leaf}" opacity="0.8"/>',
        ]
    )


def lamp(x: int, palette: dict[str, str]) -> str:
    return "".join(
        [
            rect(x + 28, 300, 6, 160, palette["wood"]),
            f'<polygon points="{x},{300} {x + 62},{300} {x + 50},{252} {x + 12},{252}" '
            f'fill="{palette["accent"]}"/>',
            rect(x + 8, 458, 46, 8, palette["wood"], ' rx="4"'),
        ]
    )


FURNITURE = {"sofa": sofa, "table": table, "shelf": shelf, "bed": bed}


def build_scene(index: int) -> tuple[str, dict[str, str]]:
    palette = PALETTES[index % len(PALETTES)]
    window_side = ["left", "centre", "right"][index % 3]
    furniture_kind = ["sofa", "table", "shelf", "bed"][index % 4]
    rug_shape = "ellipse" if index % 2 == 0 else "rect"

    pieces = [
        rect(0, 0, WIDTH, FLOOR_LINE, palette["wall"]),
        rect(0, FLOOR_LINE, WIDTH, HEIGHT - FLOOR_LINE, palette["floor"]),
        rect(0, FLOOR_LINE - 10, WIDTH, 10, palette["wood"], ' opacity="0.35"'),
        window(WINDOW_X[window_side], palette),
        rug(rug_shape, palette),
    ]

    if furniture_kind == "sofa":
        pieces.append(sofa(250, palette))
    elif furniture_kind == "table":
        pieces.append(table(280, palette))
    elif furniture_kind == "shelf":
        pieces.append(shelf(300, palette))
    else:
        pieces.append(bed(270, palette))

    if index % 5 == 0:
        pieces.append(lamp(120 if window_side != "left" else 640, palette))
    else:
        pieces.append(plant(90 if window_side == "right" else 660, palette))

    meta = {
        "file": f"room-{index + 1:02d}.svg",
        "title": ROOMS[index % len(ROOMS)],
        "style": STYLES[index % len(STYLES)],
        "palette": palette["name"],
    }
    body = "".join(pieces)
    svg = (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {WIDTH} {HEIGHT}" '
        f'width="{WIDTH}" height="{HEIGHT}" role="img">'
        f"<title>{meta['style']} {meta['title']}</title>{body}</svg>"
    )
    return svg, meta


def main() -> None:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    manifest: list[dict[str, str]] = []

    for index in range(COUNT):
        svg, meta = build_scene(index)
        (OUTPUT / meta["file"]).write_text(svg, encoding="utf-8")
        manifest.append(meta)

    (OUTPUT / "manifest.json").write_text(
        json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
    )
    print(f"wrote {len(manifest)} images and manifest.json to {OUTPUT}")


if __name__ == "__main__":
    main()