"""Draw numbered callouts on the testing screenshots.

One-off maintenance script. Run it from the repository root with the backend
virtual environment, which already carries Pillow:

    backend/.venv/Scripts/python.exe testing/annotate_shots.py

Each entry gives the source file, the output file, and the boxes to mark. Boxes
are in pixels of the 1264x974 capture.
"""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).resolve().parent
SHOTS = HERE / "screenshots"

INK = (194, 65, 12)
LEGEND_HEIGHT = 74
FONT = "C:/Windows/Fonts/segoeuib.ttf"
FONT_PLAIN = "C:/Windows/Fonts/segoeui.ttf"

PLAN: dict[str, dict] = {
    "01-login": {
        "out": "01-login.png",
        "boxes": [
            ((426, 238, 838, 284), "Email field: type the tester address"),
            ((426, 322, 838, 368), "Password field: passw0rd123"),
            ((426, 386, 838, 426), "Press Sign in"),
        ],
    },
    "02-search": {
        "out": "02-search.png",
        "boxes": [
            ((176, 197, 1088, 407), "Filters: keyword, room, style, budget slider"),
            ((176, 428, 520, 460), "How many projects matched"),
            ((176, 476, 466, 880), "One card per project: photo, room, designer, budget"),
        ],
    },
    "03-project": {
        "out": "03-project.png",
        "boxes": [
            ((934, 98, 1092, 146), "Save to shortlist, the customer action"),
            ((176, 212, 752, 640), "The project photo"),
            ((756, 212, 1088, 716), "Budget, and the view and save counters"),
        ],
    },
    "04-quote": {
        "out": "04-quote.png",
        "boxes": [
            ((1004, 98, 1094, 126), "Request state"),
            ((176, 356, 724, 620), "Every version: v1 superseded, v2 accepted"),
            ((748, 212, 1088, 428), "Nothing left to decide on a closed request"),
        ],
    },
    "05-answer": {
        "out": "05-answer.png",
        "boxes": [
            ((748, 272, 1088, 900), "The designer answers here"),
            ((772, 724, 1068, 770), "Send quote, or Decline to quote below"),
            ((176, 272, 724, 392), "What the customer asked for"),
        ],
    },
    "06-platform": {
        "out": "06-platform.png",
        "boxes": [
            ((204, 258, 1058, 332), "Add a category by name"),
            ((204, 344, 1088, 920), "Archive hides it from customers, Restore brings it back"),
            ((176, 934, 1088, 968), "Activity report continues below"),
        ],
    },
    "07-download": {
        "out": "07-download.png",
        "boxes": [
            ((812, 260, 926, 296), "Press Code, then Download ZIP"),
            ((36, 575, 920, 782), "These five .bat files are the ones you double-click"),
            ((36, 823, 920, 850), "TESTING.md is the guide you are reading"),
        ],
    },
}


def draw_one(name: str, plan: dict) -> None:
    source = SHOTS / f"raw-{name}.png"
    image = Image.open(source).convert("RGB")
    canvas = Image.new("RGB", (image.width, image.height + LEGEND_HEIGHT), (255, 255, 255))
    canvas.paste(image, (0, 0))
    draw = ImageDraw.Draw(canvas)
    badge_font = ImageFont.truetype(FONT, 18)
    caption_font = ImageFont.truetype(FONT_PLAIN, 15)
    title_font = ImageFont.truetype(FONT, 15)

    for number, (box, _caption) in enumerate(plan["boxes"], start=1):
        left, top, right, bottom = box
        draw.rounded_rectangle(box, radius=8, outline=INK, width=3)
        cx, cy = left, top
        draw.ellipse((cx - 15, cy - 15, cx + 15, cy + 15), fill=INK)
        text = str(number)
        width = draw.textlength(text, font=badge_font)
        draw.text((cx - width / 2, cy - 11), text, font=badge_font, fill=(255, 255, 255))

    draw.line((0, image.height, canvas.width, image.height), fill=(220, 220, 215), width=2)
    x = 18
    for number, (_box, caption) in enumerate(plan["boxes"], start=1):
        label = f"{number}  {caption}"
        draw.text((x, image.height + 12), label, font=title_font, fill=(31, 33, 37))
        x += draw.textlength(label, font=title_font) + 28
        if x > canvas.width - 260:
            x = 18

    canvas.save(SHOTS / plan["out"], optimize=True)
    print(f"wrote {plan['out']}  {canvas.size}")


def main() -> None:
    for name, plan in PLAN.items():
        if not (SHOTS / f"raw-{name}.png").exists():
            print(f"skip {name}, no raw capture")
            continue
        draw_one(name, plan)
    for raw in sorted(SHOTS.glob("raw-*.png")):
        raw.unlink()
    print("raw captures removed")


if __name__ == "__main__":
    main()