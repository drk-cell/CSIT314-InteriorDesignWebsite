"""The full feature tour: every role, every feature, about nine minutes.

    python testing/demo/prepare_tour.py     # once, after seed_all.py
    python testing/demo/demo_tour.py --dry  # speed 3, no video
    python testing/demo/demo_tour.py        # the take at speed 1

Same capture rules as demo_drive.py: Playwright records the page, a CSS arrow
draws the pointer, and the password manager is off before Chromium starts.
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
ROOT = HERE.parent.parent
RAW = HERE / "raw"
OUT = HERE / "CSIT314-interior-design-tour.mp4"
VIEW = {"width": 1600, "height": 1000}
PASSWORD = "passw0rd123"
PHOTOS = ROOT / "frontend" / "public" / "portfolio"

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
        locator.type(text, delay=max(8, int(30 / self.speed)))
        self.beat(pause)

    def select(self, selector: str, value: str, pause: int = 700) -> None:
        self.page.select_option(selector, value)
        self.beat(pause)


def sign_in(demo: Demo, email: str) -> None:
    """Sign in, signing the current user out first when a session is open."""
    page = demo.page
    page.goto(f"{WEB}/login", wait_until="networkidle")
    try:
        page.wait_for_selector("#login-email", timeout=2000)
    except Exception:
        demo.click(page.get_by_role("button", name="Sign out"), pause=900)
        page.goto(f"{WEB}/login", wait_until="networkidle")
    demo.beat(500)
    demo.fill(page.locator("#login-email"), email, pause=250)
    demo.fill(page.locator("#login-password"), PASSWORD, pause=250)
    demo.click(page.get_by_role("button", name="Sign in"), pause=1500)


def run(demo: Demo) -> None:
    page = demo.page

    # ---------------- designer: profile, portfolio, quote answer
    demo.mark("designer signs in")
    sign_in(demo, "verde@example.com")
    demo.beat(1200)  # the account card

    demo.mark("company profile")
    demo.click(page.get_by_role("link", name="Profile"), pause=900)
    demo.beat(700)
    page.mouse.wheel(0, 500)
    demo.beat(2200)  # location, meeting address, video call link
    demo.click(page.get_by_role("button", name="Save changes"), pause=900)
    demo.beat(1400)

    demo.mark("create project with photos")
    demo.click(page.get_by_role("link", name="My Projects"), pause=800)
    demo.click(page.get_by_role("link", name="Create New Project"), pause=900)
    demo.beat(500)
    demo.fill(page.locator("#project-title"), "Courtyard Reading Room", pause=300)
    demo.fill(
        page.locator("#project-desc"),
        "A quiet reading corner built around a planted courtyard, oak shelves "
        "and a linen window seat.",
        pause=300,
    )
    demo.select("#project-category", "Living Room", pause=400)
    demo.select("#project-style", "Minimal", pause=400)
    files = sorted(str(p) for p in (PHOTOS / "photos").glob("*.jpg"))[:2]
    if not files:
        raise SystemExit("no demo photos under frontend/public/portfolio/photos")
    # One file per picker event, each with its own wait: a two-file batch is
    # where an upload race showed up, and the slower path reads better anyway.
    page.set_input_files("#project-images", files[0])
    page.wait_for_function(
        "() => document.querySelectorAll('.queue-item').length === 1", timeout=30_000
    )
    demo.beat(800)
    page.set_input_files("#project-images", files[1])
    page.wait_for_function(
        "() => document.querySelectorAll('.queue-item').length === 2", timeout=30_000
    )
    demo.beat(900)
    page.wait_for_selector("button.tag-chip", timeout=30_000)
    demo.beat(1500)  # the suggestion chips
    demo.click(page.locator("button.tag-chip").first, pause=500)
    demo.click(page.locator("button.tag-chip").first, pause=700)
    demo.click(page.get_by_role("button", name="Create Project"), pause=1400)
    demo.beat(1200)

    demo.mark("edit project details")
    demo.beat(600)  # the create lands on the new project's edit page
    demo.fill(
        page.locator("#project-desc"),
        "A quiet reading corner built around a planted courtyard, oak shelves, "
        "a linen window seat and a small desk for two.",
        pause=300,
    )
    demo.click(page.get_by_role("button", name="Update Project"), pause=1200)
    demo.beat(900)
    demo.click(page.get_by_role("link", name="My Projects"), pause=900)
    demo.beat(1500)  # the refreshed card

    demo.mark("designer answers a quote request")
    demo.click(page.get_by_role("link", name="Quote inbox"), pause=1000)
    demo.beat(1500)
    demo.click(
        page.get_by_role("link", name="Open plan kitchen and dining"), pause=1000
    )
    demo.beat(2000)
    demo.fill(page.locator("#quote-total"), "42000", pause=300)
    demo.fill(page.locator("#quote-days"), "21", pause=300)
    demo.fill(
        page.locator("#quote-note"),
        "Cabinetry, quartz worktop, island and lighting. Site survey included.",
        pause=400,
    )
    demo.click(page.get_by_role("button", name="Send quote"), pause=1200)
    demo.beat(1800)

    # ---------------- customer: counter, search, favourites, booking, report
    demo.mark("customer signs in")
    sign_in(demo, "casey@example.com")
    demo.beat(900)

    demo.mark("customer reads the quote and counters")
    demo.click(page.get_by_role("link", name="Requests"), pause=900)
    demo.beat(1200)
    demo.click(
        page.get_by_role("link", name="Open plan kitchen and dining"), pause=900
    )
    demo.beat(2200)  # total, GST, validity
    demo.fill(page.locator("#target-price"), "38000", pause=300)
    demo.fill(
        page.locator("#target-note"),
        "We can go ahead this month if the price lands near thirty-eight.",
        pause=300,
    )
    demo.click(page.get_by_role("button", name="Send target"), pause=1100)
    demo.beat(1200)

    demo.mark("customer searches and saves")
    demo.click(page.get_by_role("link", name="Find a project"), pause=900)
    demo.beat(700)
    demo.select("#search-category", "Living Room", pause=500)
    demo.select("#search-style", "Minimal", pause=600)
    box = page.locator('input[aria-label="Maximum budget"]').bounding_box()
    page.mouse.move(box["x"] + box["width"] * 0.9, box["y"] + box["height"] / 2, steps=12)
    demo.beat(200)
    page.mouse.click(box["x"] + box["width"] * 0.30, box["y"] + box["height"] / 2)
    demo.beat(1600)
    demo.click(page.get_by_role("link", name="Warm Minimal Living Room"), pause=1200)
    demo.beat(1800)
    demo.click(page.get_by_role("button", name="Save to shortlist"), pause=900)
    demo.beat(1400)

    demo.mark("customer searches with a photo")
    demo.click(page.get_by_role("link", name="Find a project"), pause=900)
    demo.beat(600)
    page.set_input_files('input[type="file"]', files[0])
    demo.beat(2500)  # tags come back, the list reranks
    page.mouse.wheel(0, 200)
    demo.beat(2200)
    page.mouse.wheel(0, -200)
    demo.beat(600)

    demo.mark("customer removes a favourite")
    demo.click(page.get_by_role("link", name="Saved"), pause=900)
    demo.beat(1200)
    demo.click(page.get_by_role("button", name="Remove").first, pause=900)
    demo.beat(1400)

    demo.mark("customer books a consultation")
    demo.click(page.get_by_role("link", name="Designers"), pause=900)
    demo.beat(700)
    studio = page.locator(
        "article.card", has=page.get_by_role("heading", name="Studio Verde")
    ).first
    demo.click(studio.get_by_role("link", name="View profile"), pause=1000)
    demo.beat(1000)
    demo.click(page.get_by_role("link", name="Book a consultation"), pause=1200)
    demo.beat(600)
    demo.click(page.get_by_role("button", name="Video call"), pause=600)
    tomorrow = (date.today() + timedelta(days=1)).isoformat()
    demo.select("#appointment-day", tomorrow, pause=1000)
    demo.click(page.get_by_role("button", name="11:00"), pause=600)
    demo.fill(
        page.locator("#appointment-requirements"),
        "Warm light and a place to pin samples.",
        pause=300,
    )
    demo.click(page.get_by_role("button", name="Book this time"), pause=1200)
    demo.beat(2200)

    demo.mark("customer reports a project")
    demo.click(page.get_by_role("link", name="Find a project"), pause=900)
    demo.beat(600)
    demo.fill(page.locator("#search-keyword"), "Soft Neutral Bedroom", pause=900)
    demo.beat(800)
    demo.click(page.get_by_role("link", name="Soft Neutral Bedroom"), pause=1000)
    demo.beat(1500)
    demo.click(page.get_by_role("link", name="Report this project"), pause=1000)
    demo.beat(500)
    demo.select("#report-reason", "Spam or misleading", pause=600)
    demo.fill(
        page.locator("#report-comments"),
        "These photos look like stock images, not this studio's own work.",
        pause=300,
    )
    demo.click(page.get_by_role("button", name="Send report"), pause=1100)
    demo.beat(2000)

    # ---------------- designer: revise the quote, accept the booking
    demo.mark("designer revises the quote")
    sign_in(demo, "verde@example.com")
    demo.click(page.get_by_role("link", name="Quote inbox"), pause=900)
    demo.beat(900)
    demo.click(
        page.get_by_role("link", name="Open plan kitchen and dining"), pause=900
    )
    demo.beat(1800)  # the counter is on screen
    demo.fill(page.locator("#quote-total"), "40500", pause=300)
    demo.fill(
        page.locator("#quote-note"),
        "Revised: worktop upgraded, lighting kept. Same scope.",
        pause=300,
    )
    demo.click(page.get_by_role("button", name="Send new version"), pause=1100)
    demo.beat(1600)

    demo.mark("designer accepts the consultation")
    demo.click(page.get_by_role("link", name="Consultations"), pause=900)
    demo.beat(1000)
    demo.click(page.get_by_role("button", name="Accept").first, pause=1000)
    demo.beat(1600)

    # ---------------- customer: accept the quote, see the meeting link
    demo.mark("customer accepts the quote")
    sign_in(demo, "casey@example.com")
    demo.click(page.get_by_role("link", name="Requests"), pause=900)
    demo.beat(900)
    demo.click(
        page.get_by_role("link", name="Open plan kitchen and dining"), pause=900
    )
    demo.beat(1600)
    demo.click(page.get_by_role("button", name="Accept quote"), pause=1100)
    demo.beat(2000)

    demo.mark("customer sees the meeting link")
    demo.click(page.get_by_role("link", name="Appointments"), pause=900)
    demo.beat(900)
    page.mouse.wheel(0, 260)
    demo.beat(2400)
    page.mouse.wheel(0, -260)
    demo.beat(500)

    # ---------------- admin: reports, suspension, approval
    demo.mark("admin reviews the report")
    sign_in(demo, "admin@example.com")
    demo.beat(900)
    demo.click(page.get_by_role("link", name="Admin"), pause=1000)
    demo.beat(900)
    page.mouse.wheel(0, 900)
    demo.beat(1800)  # the reported projects table
    demo.click(page.get_by_label("Take down project").first, pause=400)
    demo.click(page.get_by_label("Suspend designer").first, pause=400)
    demo.beat(600)
    demo.click(page.get_by_role("button", name="Apply and close").first, pause=1200)
    demo.beat(1600)

    demo.mark("admin approves a designer")
    demo.select("#admin-filter", "PENDING", pause=1000)
    demo.beat(900)
    demo.click(page.get_by_role("button", name="Approve").first, pause=1100)
    demo.beat(1600)
    demo.select("#admin-filter", "ACTIVE", pause=900)
    demo.beat(1400)

    demo.mark("admin manages categories and reports")
    demo.click(page.get_by_role("link", name="Platform", exact=True), pause=1000)
    demo.beat(1200)
    demo.fill(page.locator("#new-category"), "Loft", pause=400)
    demo.click(page.get_by_role("button", name="Add", exact=True), pause=1200)
    demo.beat(1400)
    demo.select("#report-period", "weekly", pause=900)
    demo.beat(1600)
    page.mouse.wheel(0, 380)
    demo.beat(2000)
    page.mouse.wheel(0, -380)
    demo.beat(500)

    # Closing shot: the suspended studio tries to sign in and is refused. The
    # accounts filter stalls on "Loading accounts" in this build, so the login
    # refusal is the honest proof that the suspension took effect.
    demo.mark("suspended studio cannot sign in")
    demo.click(page.get_by_role("button", name="Sign out"), pause=900)
    page.goto(f"{WEB}/login", wait_until="networkidle")
    demo.beat(600)
    demo.fill(page.locator("#login-email"), "verde@example.com", pause=200)
    demo.fill(page.locator("#login-password"), PASSWORD, pause=200)
    demo.click(page.get_by_role("button", name="Sign in"), pause=1200)
    demo.beat(3000)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry", action="store_true", help="no video, three times faster")
    parser.add_argument("--speed", type=float, default=1.0)
    args = parser.parse_args()
    speed = 3.0 if args.dry else args.speed

    profile = RAW / "tour-profile"
    recording = RAW / "tour-video"
    if profile.exists():
        shutil.rmtree(profile, ignore_errors=True)
    if recording.exists():
        shutil.rmtree(recording, ignore_errors=True)
    profile.mkdir(parents=True)
    (profile / "Default").mkdir()
    (profile / "Default" / "Preferences").write_text(
        json.dumps(
            {
                "credentials_enable_service": False,
                "credentials_enable_autosignin": False,
                "profile": {
                    "password_manager_enabled": False,
                    "password_manager_leak_detection": False,
                    "exit_type": "Normal",
                },
                "autofill": {"profile_enabled": False, "credit_card_enabled": False},
                "browser": {"has_seen_welcome_page": True, "check_default_browser": False},
            }
        ),
        encoding="utf-8",
    )

    path = None
    with sync_playwright() as playwright:
        context = playwright.chromium.launch_persistent_context(
            str(profile),
            headless=False,
            viewport=VIEW,
            record_video_dir=None if args.dry else str(recording),
            record_video_size=None if args.dry else VIEW,
            ignore_default_args=["--enable-automation"],
            args=[
                "--window-position=0,0",
                "--window-size=1600,1000",
                "--disable-save-password-bubble",
                "--password-store=basic",
                "--no-first-run",
                "--no-default-browser-check",
                "--hide-crash-restore-bubble",
                "--disable-infobars",
                "--disable-search-engine-choice-screen",
                "--disable-sync",
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
        context.close()
        if video is not None:
            path = video.path()

    if path is None:
        print("dry run complete, no video")
        return 0

    print("raw video", path)
    subprocess.run(
        [
            "ffmpeg", "-y", "-ss", "1.0", "-i", str(path),
            "-c:v", "libx264", "-preset", "slow", "-crf", "25",
            "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(OUT),
        ],
        check=True,
    )
    probe = subprocess.run(
        [
            "ffprobe", "-v", "error", "-show_entries", "format=duration,size",
            "-of", "default=nw=1", str(OUT),
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    print(probe.stdout.strip())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
