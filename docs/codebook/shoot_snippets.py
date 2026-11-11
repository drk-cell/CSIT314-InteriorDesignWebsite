"""Photograph every rendered snippet.

Each section in snippets.html is a VS Code window with the dark-plus theme.
Playwright screenshots one element at a time, at twice the pixel density so the
text stays sharp when the document scales the picture to page width.

    python docs/codebook/shoot_snippets.py
"""

from __future__ import annotations

import json
from pathlib import Path

from playwright.sync_api import sync_playwright

HERE = Path(__file__).resolve().parent
RENDER = HERE / "render"
SHOTS = HERE / "shots"
HTML = RENDER / "snippets.html"


def main() -> int:
    rows = json.loads((RENDER / "snippets.json").read_text(encoding="utf-8"))
    SHOTS.mkdir(exist_ok=True)

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        page = browser.new_page(viewport={"width": 1700, "height": 1200}, device_scale_factor=2)
        page.goto(HTML.as_uri(), wait_until="load")
        page.wait_for_timeout(400)

        missing = []
        for index, row in enumerate(rows, start=1):
            element = page.locator(f"#{row['key']}")
            if element.count() == 0:
                missing.append(row["key"])
                continue
            # Widen the frame to the widest line so no code is cut off on the right.
            element.evaluate(
                """node => {
                    const pre = node.querySelector('.shiki');
                    const lines = [...pre.querySelectorAll('.line')];
                    let widest = 0;
                    for (const line of lines) {
                        const range = document.createRange();
                        range.selectNodeContents(line);
                        widest = Math.max(widest, range.getBoundingClientRect().width);
                    }
                    const width = Math.max(760, Math.ceil(widest + 95));
                    pre.style.width = width + 'px';
                    node.style.width = width + 'px';
                }"""
            )
            element.screenshot(path=str(SHOTS / f"{row['key']}.png"))
            if index % 25 == 0:
                print(f"  {index}/{len(rows)}")

        browser.close()

    total = sum(path.stat().st_size for path in SHOTS.glob("*.png"))
    print(f"wrote {len(rows) - len(missing)} pictures to {SHOTS} · {total // 1024 // 1024} MB")
    if missing:
        print("missing:", missing[:5])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
