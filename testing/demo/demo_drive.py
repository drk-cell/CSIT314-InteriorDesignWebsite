"""Drive the CSIT314 demo for all three roles and record it.

Usage, with the backend on 8010 and the frontend on 5173:

    python testing/demo/prepare_demo.py            # once, after seed_all.py
    python testing/demo/demo_drive.py --dry        # fast selector check
    python testing/demo/demo_drive.py              # the take, writes the MP4

The cursor is a CSS arrow injected into every page, so the recording shows a
pointer without touching the desktop. Playwright records the page only.
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import time
from datetime import date, timedelta
from pathlib import Path

from playwright.sync_api import Locator, Page, sync_playwright

WEB = "http://localhost:5173"
HERE = Path(__file__).resolve().parent
RAW = HERE / "raw"
OUT = HERE / "CSIT314-interior-design-demo.mp4"
VIEW = {"width": 1600, "height": 1000}
PASSWORD = "passw0rd123"

CURSOR_JS = """
(() => {
  if (window.__csitCursor) return;
  window.__csitCursor = true;
  const install = () => {
    const style = document.createElement('style');
    style.textContent = '*{cursor:none !important}';
    document.documentElement.appendChild(style);

    const cursor = document.createElement('div');
    cursor.style.cssText = 'position:fixed;left:0;top:0;width:20px;height:20px;'
      + 'z-index:2147483647;pointer-events:none;will-change:transform;'
      + 'filter:drop-shadow(0 1px 2px rgba(0,0,0,.35));';
    cursor.innerHTML = '<svg width="20" height="20" viewBox="0 0 24 24">'
      + '<path d="M5 2 L5 19 L9.5 14.6 L12.5 21 L15.2 19.7 L12.2 13.5 L18.5 13.5 Z" '
      + 'fill="#111827" stroke="#ffffff" stroke-width="1.3"/></svg>';
    document.documentElement.appendChild(cursor);

    let x = 800, y = 500;
    window.addEventListener('mousemove', (event) => {
      x = event.clientX; y = event.clientY;
      cursor.style.transform = `translate(${x - 2}px, ${y - 2}px)`;
    }, true);
    window.addEventListener('mousedown', () => {
      const ring = document.createElement('div');
      ring.style.cssText = `position:fixed;left:${x - 18}px;top:${y - 18}px;`
        + 'width:36px;height:36px;border:3px solid rgba(32,86,74,.65);'
        + 'border-radius:50%;pointer-events:none;z-index:2147483646;';
      document.documentElement.appendChild(ring);
      ring.animate(
        [{ transform: 'scale(.4)', opacity: 1 }, { transform: 'scale(1.25)', opacity: 0 }],
        { duration: 320, easing: 'ease-out' }
      ).onfinish = () => ring.remove();
    }, true);
  };
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', install);
  } else {
    install();
  }
})();
"""


class Demo:
    """Pacing and logging for one take."""

    def __init__(self, page: Page, speed: float) -> None:
        self.page = page
        self.speed = speed
        self.started = time.monotonic()

    def elapsed(self) -> float:
        return time.monotonic() - self.started

    def mark(self, label: str) -> None:
        print(f"MARK {self.elapsed():6.1f}s  {label}", flush=True)

    def beat(self, milliseconds: int) -> None:
        self.page.wait_for_timeout(max(1, int(milliseconds / self.speed)))

    def move(self, locator: Locator) -> None:
        locator.scroll_into_view_if_needed()
        box = locator.bounding_box()
        if box is None:
            return
        self.page.mouse.move(
            box["x"] + box["width"] / 2, box["y"] + box["height"] / 2, steps=20
        )

    def click(self, locator: Locator, pause: int = 700) -> None:
        self.move(locator)
        self.beat(220)
        locator.click()
        self.beat(pause)

    def fill(self, locator: Locator, text: str, pause: int = 450) -> None:
        self.move(locator)
        locator.click()
        self.beat(150)
        locator.fill("")
        locator.type(text, delay=max(8, int(32 / self.speed)))
        self.beat(pause)


def run(demo: Demo) -> None:
    page = demo.page

    # --- designer: sign in
    demo.mark("designer signs in")
    page.goto(f"{WEB}/login", wait_until="networkidle")
    demo.beat(700)
    demo.fill(page.locator("#login-email"), "verde@example.com")
    demo.fill(page.locator("#login-password"), PASSWORD)
    demo.click(page.get_by_role("button", name="Sign in"), pause=1400)

    # --- use case 1: incoming quote requests
    demo.mark("1 incoming quote requests")
    demo.click(page.get_by_role("link", name="Quote inbox"), pause=1100)
    demo.beat(1800)
    demo.click(
        page.get_by_role("link", name="Open plan kitchen and dining"), pause=1100
    )
    demo.beat(2800)
    page.mouse.wheel(0, 260)
    demo.beat(1600)
    page.mouse.wheel(0, -260)
    demo.beat(700)

    # --- use case 4: change project details
    demo.mark("4 change project details")
    demo.click(page.get_by_role("link", name="My Projects"), pause=1100)
    demo.beat(900)
    demo.click(page.get_by_role("link", name="Edit").first, pause=1100)
    demo.beat(700)
    current_title = page.locator("#project-title").input_value()
    demo.fill(
        page.locator("#project-title"),
        f"{current_title} - 2026 refresh",
        pause=600,
    )
    demo.click(page.get_by_role("button", name="Update Project"), pause=1300)
    demo.beat(1800)

    # --- switch to the customer
    demo.mark("customer signs in")
    demo.click(page.get_by_role("button", name="Sign out"), pause=1100)
    demo.fill(page.locator("#login-email"), "casey@example.com")
    demo.fill(page.locator("#login-password"), PASSWORD)
    demo.click(page.get_by_role("button", name="Sign in"), pause=1400)

    # --- use case 2: search by category, style and budget, open, save
    demo.mark("2 search, open and save")
    demo.click(page.get_by_role("link", name="Find a project"), pause=1100)
    demo.beat(800)
    page.select_option("#search-category", "Living Room")
    demo.beat(600)
    page.select_option("#search-style", "Minimal")
    demo.beat(600)

    slider = page.locator('input[aria-label="Maximum budget"]')
    box = slider.bounding_box()
    if box is not None:
        page.mouse.move(box["x"] + box["width"] * 0.96, box["y"] + box["height"] / 2, steps=16)
        demo.beat(200)
        page.mouse.click(box["x"] + box["width"] * 0.30, box["y"] + box["height"] / 2)
    demo.beat(1600)
    demo.click(
        page.get_by_role("link", name="Warm Minimal Living Room"), pause=1400
    )
    demo.beat(2200)
    demo.click(page.get_by_role("button", name="Save to shortlist"), pause=800)
    demo.beat(1700)

    # --- use case 3: remove it from the favourites
    demo.mark("3 remove from favourites")
    demo.click(page.get_by_role("link", name="Saved"), pause=1100)
    demo.beat(1100)
    demo.click(page.get_by_role("button", name="Remove").first, pause=800)
    demo.beat(1800)

    # --- use case 5: book a consultation
    demo.mark("5 book a consultation")
    demo.click(page.get_by_role("link", name="Designers"), pause=1100)
    demo.beat(700)
    studio_card = page.locator(
        "article.card", has=page.get_by_role("heading", name="Studio Verde")
    ).first
    demo.click(studio_card.get_by_role("link", name="View profile"), pause=1100)
    demo.beat(1100)
    demo.click(page.get_by_role("link", name="Book a consultation"), pause=1200)
    demo.beat(700)
    demo.click(page.get_by_role("button", name="Video call"), pause=600)
    page.select_option("#appointment-day", (date.today() + timedelta(days=1)).isoformat())
    demo.beat(900)
    demo.click(page.get_by_role("button", name="11:00"), pause=500)
    demo.fill(
        page.locator("#appointment-requirements"),
        "Warm light, keep the oak floor.",
        pause=500,
    )
    demo.click(page.get_by_role("button", name="Book this time"), pause=1100)
    demo.beat(2500)

    # --- use case 6: report a project
    demo.mark("6 report a project")
    demo.click(page.get_by_role("link", name="Find a project"), pause=1100)
    demo.beat(700)
    demo.fill(page.locator("#search-keyword"), "Soft Neutral Bedroom", pause=1100)
    demo.beat(900)
    demo.click(page.get_by_role("link", name="Soft Neutral Bedroom"), pause=1100)
    demo.beat(1700)
    demo.click(page.get_by_role("link", name="Report this project"), pause=1100)
    demo.beat(600)
    page.select_option("#report-reason", "Spam or misleading")
    demo.beat(700)
    demo.fill(
        page.locator("#report-comments"),
        "These photos look like stock images, not this studio's work.",
        pause=500,
    )
    demo.click(page.get_by_role("button", name="Send report"), pause=1000)
    demo.beat(2300)

    # --- admin: the queue that received the report
    demo.mark("admin reads the report queue")
    demo.click(page.get_by_role("button", name="Sign out"), pause=1100)
    demo.fill(page.locator("#login-email"), "admin@example.com")
    demo.fill(page.locator("#login-password"), PASSWORD)
    demo.click(page.get_by_role("button", name="Sign in"), pause=1400)
    demo.click(page.get_by_role("link", name="Admin"), pause=1300)
    demo.beat(1000)
    page.mouse.wheel(0, 640)
    demo.beat(2600)
    demo.beat(1800)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry", action="store_true", help="speed 3, no recording")
    parser.add_argument("--speed", type=float, default=1.0)
    args = parser.parse_args()

    speed = 3.0 if args.dry else args.speed
    if RAW.exists():
        shutil.rmtree(RAW)
    RAW.mkdir(parents=True, exist_ok=True)

    with sync_playwright() as playwright:
        profile = RAW / "profile"
        (profile / "Default").mkdir(parents=True, exist_ok=True)
        preferences = {
            "credentials_enable_service": False,
            "credentials_enable_autosignin": False,
            "profile": {
                "password_manager_enabled": False,
                "password_manager_leak_detection": False,
                "exit_type": "Normal",
            },
            "autofill": {"profile_enabled": False, "credit_card_enabled": False},
            "browser": {
                "has_seen_welcome_page": True,
                "check_default_browser": False,
                "show_home_button": False,
            },
            "savefile": {"prompt_for_download": False},
        }
        (profile / "Default" / "Preferences").write_text(
            json.dumps(preferences), encoding="utf-8"
        )

        context = playwright.chromium.launch_persistent_context(
            user_data_dir=str(profile),
            headless=False,
            viewport=VIEW,
            record_video_dir=None if args.dry else str(RAW / "video"),
            record_video_size=VIEW,
            ignore_default_args=["--enable-automation"],
            args=[
                "--window-position=0,0",
                "--window-size=1600,1000",
                "--disable-save-password-bubble",
                "--password-store=basic",
                "--disable-infobars",
                "--hide-crash-restore-bubble",
                "--disable-search-engine-choice-screen",
                "--disable-sync",
                "--no-first-run",
                "--no-default-browser-check",
                "--disable-blink-features=AutomationControlled",
                "--disable-features=Translate,MediaRouter,AutofillServerCommunication,"
                "PasswordLeakDetection,PrivacySandboxSettings4,"
                "OptimizationHints,InterestFeedContentSuggestions",
            ],
        )
        context.add_init_script(CURSOR_JS)
        page = context.pages[0] if context.pages else context.new_page()

        demo = Demo(page, speed)
        run(demo)
        demo.mark("end")

        video = page.video
        path = None
        context.close()
        if video is not None:
            path = video.path()

    if path is None:
        print("dry run complete, no video")
        return 0

    print("raw video", path)
    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-ss",
            "1.0",
            "-i",
            str(path),
            "-c:v",
            "libx264",
            "-preset",
            "slow",
            "-crf",
            "24",
            "-pix_fmt",
            "yuv420p",
            "-movflags",
            "+faststart",
            str(OUT),
        ],
        check=True,
    )
    probe = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration,size",
            "-of",
            "default=nw=1",
            str(OUT),
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    print(probe.stdout.strip())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
