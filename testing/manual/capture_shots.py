"""Capture one screenshot for every screen the manual describes.

The manual must show the running build, not a drawing of it. This script signs
in as each demo role through the API, sets the token the browser expects, makes
sure Casey has one answered request with Studio Verde, then opens each route and
writes a PNG under ``testing/manual/shots``.

Usage, with the backend on 8010 and the frontend on 5173:

    python testing/manual/capture_shots.py

Requires: playwright (chromium), and a seeded backend (``seed_all.py``).
"""

from __future__ import annotations

import json
from datetime import date, timedelta
from pathlib import Path

from playwright.sync_api import Page, sync_playwright

API = "http://127.0.0.1:8010/api"
WEB = "http://localhost:5173"
SHOTS = Path(__file__).resolve().parent / "shots"
VIEWPORT = {"width": 1440, "height": 900}

ACCOUNTS = {
    "customer": ("casey@example.com", "passw0rd123"),
    "designer": ("verde@example.com", "passw0rd123"),
    "admin": ("admin@example.com", "passw0rd123"),
}


def call(page: Page, method: str, path: str, body: dict | None = None):
    """Call the API with the token in localStorage and return parsed JSON."""
    return page.evaluate(
        """async ([api, method, path, body]) => {
            const token = localStorage.getItem('idp.token');
            const response = await fetch(api + path, {
                method,
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': 'Bearer ' + token,
                },
                body: body === null ? undefined : JSON.stringify(body),
            });
            const text = await response.text();
            let parsed = null;
            try { parsed = text ? JSON.parse(text) : null; } catch { parsed = text; }
            return {status: response.status, body: parsed};
        }""",
        [API, method, path, body],
    )


def sign_in(page: Page, role: str) -> None:
    email, password = ACCOUNTS[role]
    token = page.evaluate(
        """async ([api, email, password]) => {
            const response = await fetch(api + '/auth/login', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({email, password}),
            });
            const body = await response.json();
            return body.access_token;
        }""",
        [API, email, password],
    )
    if token is None:
        raise SystemExit(f"cannot sign in as {role}")
    page.evaluate("token => localStorage.setItem('idp.token', token)", token)


def shoot(page: Page, name: str, anchor: str | None = None) -> None:
    """Save the viewport, optionally scrolled so an element is in view."""
    if anchor is not None:
        page.eval_on_selector(
            anchor, "element => element.scrollIntoView({block: 'start'})"
        )
    page.wait_for_timeout(700)
    target = SHOTS / f"{name}.png"
    page.screenshot(path=str(target), full_page=False)
    print("shot", target.name)


def main() -> int:
    SHOTS.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        page = browser.new_page(viewport=VIEWPORT, device_scale_factor=1)

        page.goto(f"{WEB}/login", wait_until="networkidle")
        shoot(page, "01-login")
        page.goto(f"{WEB}/register", wait_until="networkidle")
        shoot(page, "02-register")

        # ----- customer
        page.goto(f"{WEB}/login", wait_until="networkidle")
        sign_in(page, "customer")

        requests = call(page, "GET", "/quotes/requests")["body"] or []
        if not requests:
            companies = call(page, "GET", "/companies")["body"] or []
            studio = next(
                (row for row in companies if "Verde" in row.get("name", "")),
                companies[0],
            )
            created = call(
                page,
                "POST",
                "/quotes/requests",
                {
                    "company_id": studio["id"],
                    "title": "Open plan kitchen and dining",
                    "scope": "Remove one wall, rebuild the kitchen and fit new lighting.",
                    "budget_min_cents": 3000000,
                    "budget_max_cents": 5000000,
                },
            )
            print("created request", created["status"])

        page.goto(f"{WEB}/dashboard", wait_until="networkidle")
        shoot(page, "03-customer-dashboard")

        page.goto(f"{WEB}/search", wait_until="networkidle")
        shoot(page, "04b-customer-search")

        page.goto(f"{WEB}/search", wait_until="networkidle")
        page.set_input_files(
            ".photo-search input[type=file]",
            str(
                Path(__file__).resolve().parents[2]
                / "frontend"
                / "public"
                / "portfolio"
                / "photos"
                / "photo-04.jpg"
            ),
        )
        page.wait_for_timeout(2500)
        shoot(page, "04-customer-photo-search")

        project_id = (call(page, "GET", "/projects/search?page_size=1")["body"]["items"])[
            0
        ]["id"]
        page.goto(f"{WEB}/projects/{project_id}", wait_until="networkidle")

        saved = call(page, "GET", "/shortlist")["body"].get("project_ids", [])
        if len(saved) < 2:
            items = call(page, "GET", "/projects/search?page_size=3")["body"]["items"]
            for row in items:
                if row["id"] not in saved:
                    call(page, "POST", f"/shortlist/{row['id']}")
                    saved.append(row["id"])
            page.goto(f"{WEB}/projects/{project_id}", wait_until="networkidle")

        shoot(page, "05-customer-project")

        page.goto(f"{WEB}/saved", wait_until="networkidle")
        shoot(page, "06-customer-saved")

        request_id = requests[0]["id"] if requests else None
        if request_id is None:
            request_id = (call(page, "GET", "/quotes/requests")["body"])[0]["id"]

        detail = call(page, "GET", f"/quotes/requests/{request_id}")["body"]
        company_id = detail["company_id"]
        page.goto(f"{WEB}/quotes/new/{company_id}", wait_until="networkidle")
        shoot(page, "07-customer-request-quote")

        # A consultation, so the booking page and both appointment lists are real.
        appointments = call(page, "GET", "/appointments")["body"] or []
        already_open = any(
            row["company_id"] == company_id and row["state"] != "CANCELLED"
            for row in appointments
        )
        if not already_open:
            day = (date.today() + timedelta(days=1)).isoformat()
            booked = call(
                page,
                "POST",
                "/appointments",
                {
                    "company_id": company_id,
                    "date": day,
                    "time": "15:00",
                    "requirements": "Warm light and a calm palette.",
                },
            )
            print("booked consultation", booked["status"])

        page.goto(f"{WEB}/designers/{company_id}/book", wait_until="networkidle")
        page.select_option(
            "#appointment-day", (date.today() + timedelta(days=1)).isoformat()
        )
        page.wait_for_timeout(900)
        shoot(page, "19-customer-booking")

        page.goto(f"{WEB}/appointments", wait_until="networkidle")
        shoot(page, "20-customer-appointments")

        # ----- designer
        page.evaluate("localStorage.removeItem('idp.token')")
        page.goto(f"{WEB}/login", wait_until="networkidle")
        sign_in(page, "designer")

        # Answer the request once so the customer sees a real quote.
        existing = call(page, "GET", f"/quotes/requests/{request_id}")["body"]
        if not existing.get("quotes"):
            answer = call(
                page,
                "POST",
                f"/quotes/requests/{request_id}/quotes",
                {
                    "total_cents": 485500,
                    "valid_days": 14,
                    "gst_included": False,
                    "note": "Includes the wall removal and the new lighting circuit.",
                },
            )
            print("answered", answer["status"])

        page.goto(f"{WEB}/dashboard", wait_until="networkidle")
        shoot(page, "09-designer-dashboard")

        page.goto(f"{WEB}/projects/new", wait_until="networkidle")
        for name in ("photo-01.jpg", "photo-07.jpg"):
            page.set_input_files(
                "#project-images",
                str(
                    Path(__file__).resolve().parents[2]
                    / "frontend"
                    / "public"
                    / "portfolio"
                    / "photos"
                    / name
                ),
            )
            page.wait_for_timeout(2000)
        page.wait_for_timeout(1000)
        shoot(page, "10-designer-project-editor", anchor=".image-queue")

        page.goto(f"{WEB}/projects", wait_until="networkidle")
        shoot(page, "11-designer-projects")

        page.goto(f"{WEB}/quotes", wait_until="networkidle")
        shoot(page, "12-designer-inbox")

        page.goto(f"{WEB}/appointments", wait_until="networkidle")
        shoot(page, "21-designer-appointments")

        page.goto(f"{WEB}/quotes/{request_id}", wait_until="networkidle")
        shoot(page, "13-designer-answer")

        page.goto(f"{WEB}/profile", wait_until="networkidle")
        shoot(page, "14-designer-company")

        mine = call(page, "GET", "/companies/me")["body"]["id"]
        page.goto(f"{WEB}/designers/{mine}", wait_until="networkidle")
        shoot(page, "15-designer-portfolio")

        # ----- admin
        page.evaluate("localStorage.removeItem('idp.token')")
        page.goto(f"{WEB}/login", wait_until="networkidle")
        sign_in(page, "admin")

        page.goto(f"{WEB}/platform", wait_until="networkidle")
        shoot(page, "16-admin-platform")

        page.goto(f"{WEB}/platform", wait_until="networkidle")
        page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        page.wait_for_timeout(900)
        shoot(page, "18-admin-reports")

        page.goto(f"{WEB}/admin", wait_until="networkidle")
        shoot(page, "17-admin-accounts")

        # ----- back to the customer for the accepted-quote screen
        page.evaluate("localStorage.removeItem('idp.token')")
        page.goto(f"{WEB}/login", wait_until="networkidle")
        sign_in(page, "customer")
        page.goto(f"{WEB}/quotes/{request_id}", wait_until="networkidle")
        shoot(page, "08-customer-quote")

        browser.close()

    names = sorted(SHOTS.glob("*.png"))
    print(json.dumps({"count": len(names), "dir": str(SHOTS)}, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
