"""Seed the demo: three designers, three companies, eight projects, one customer.

Run against a fresh backend on http://127.0.0.1:8000. The admin credentials
come from APP_ADMIN_EMAIL and APP_ADMIN_PASSWORD.

Usage: python scripts/seed_demo.py
"""

from __future__ import annotations

import os
from datetime import date, timedelta
from pathlib import Path

import httpx

BASE = os.environ.get("DEMO_BASE", "http://127.0.0.1:8000/api")
ADMIN_EMAIL = os.environ.get("APP_ADMIN_EMAIL", "admin@example.com")
ADMIN_PASSWORD = os.environ.get("APP_ADMIN_PASSWORD", "change-me")

DESIGNERS = [
    {
        "email": "verde@example.com",
        "name": "Studio Verde",
        "location": "Singapore",
        "meeting_address": "18 Duxton Road, #02-01, Singapore 089483",
        "call_link": "https://meet.google.com/studio-verde",
        "contact_email": "hello@studioverde.sg",
        "contact_phone": "+65 6000 1000",
        "projects": [
            ("Warm Minimal Living Room", "Minimal", "Living Room", 20000, 40000, "photo-01.jpg"),
            ("Soft Neutral Bedroom", "Scandinavian", "Bedroom", 25000, 50000, "photo-05.jpg"),
            ("Open Birch Kitchen", "Scandinavian", "Kitchen", 30000, 65000, "photo-07.jpg"),
        ],
    },
    {
        "email": "nordic@example.com",
        "name": "Nordic Haus",
        "location": "Kuala Lumpur",
        "meeting_address": "12 Jalan Bangsar, Level 3, Kuala Lumpur 59000",
        "call_link": "https://zoom.us/j/nordic-haus",
        "contact_email": "hello@nordichaus.my",
        "contact_phone": "+60 3 6000 2000",
        "projects": [
            ("Cool Grey Study", "Contemporary", "Home Office", 15000, 35000, "photo-13.jpg"),
            ("Linen Bedroom", "Minimal", "Bedroom", 22000, 48000, "photo-14.jpg"),
            ("Panel Dining Room", "Traditional", "Dining Room", 35000, 70000, "photo-10.jpg"),
        ],
    },
    {
        "email": "atelier@example.com",
        "name": "Atelier One",
        "location": "Singapore",
        "meeting_address": "88 Club Street, #01-02, Singapore 069452",
        "call_link": "https://teams.microsoft.com/l/meetup-join/atelier-one",
        "contact_email": "hello@atelierone.sg",
        "contact_phone": "+65 6000 3000",
        "projects": [
            ("Bold Kitchen", "Contemporary", "Kitchen", 40000, 80000, "photo-08.jpg"),
            ("Curated Living Room", "Japandi", "Living Room", 30000, 60000, "photo-03.jpg"),
        ],
    },
]

PASSWORD = "passw0rd123"


def main() -> None:
    """Seed everything and print a short report."""
    with httpx.Client(base_url=BASE, timeout=30) as client:
        admin_token = login(client, ADMIN_EMAIL, ADMIN_PASSWORD)
        for designer in DESIGNERS:
            account_id = register(
                client, designer["email"], PASSWORD, designer["name"], "DESIGNER"
            )
            client.post(
                f"/admin/accounts/{account_id}/approve",
                headers=auth(admin_token),
            )
            token = login(client, designer["email"], PASSWORD)
            client.post(
                "/companies",
                headers=auth(token),
                json={
                    "name": designer["name"],
                    "description": "Residential interiors with a calm, warm feel.",
                    "contact_email": designer["contact_email"],
                    "contact_phone": designer["contact_phone"],
                    "location": designer["location"],
                    "meeting_address": designer["meeting_address"],
                    "call_link": designer["call_link"],
                },
            )
            for title, style, category, low, high, image in designer["projects"]:
                tags = photo_tags(client, token, image)
                response = client.post(
                    "/projects",
                    headers=auth(token),
                    json={
                        "title": title,
                        "description": "A home that breathes: layout, light and texture tuned for daily life.",
                        "style": style,
                        "category": category,
                        "budget_min": low,
                        "budget_max": high,
                        "images": [f"/portfolio/photos/{image}"],
                        "tags": tags,
                    },
                )
                response.raise_for_status()
            print(f"seeded {designer['name']}: {len(designer['projects'])} projects")
        register(client, "casey@example.com", PASSWORD, "Casey Tan", "CUSTOMER")
        print("seeded customer: casey@example.com")

        # The customer starts with a shortlist, so the saved page has content.
        customer_token = login(client, "casey@example.com", PASSWORD)
        page = client.get(
            "/projects/search", headers=auth(customer_token), params={"page_size": 20}
        ).json()
        for project in page["items"][:3]:
            client.post(f"/shortlist/{project['id']}", headers=auth(customer_token))
        print(f"saved {min(3, len(page['items']))} projects to the customer shortlist")

        # Two consultations: one waits for the designer, one is already accepted.
        companies = client.get("/companies", headers=auth(customer_token)).json()
        by_name = {row["name"]: row for row in companies}
        day = (date.today() + timedelta(days=2)).isoformat()
        for name, time, mode, accept_as in (
            ("Studio Verde", "10:00", "IN_PERSON", None),
            ("Nordic Haus", "14:00", "ONLINE", "nordic@example.com"),
        ):
            company = by_name.get(name)
            if company is None:
                continue
            response = client.post(
                "/appointments",
                headers=auth(customer_token),
                json={
                    "company_id": company["id"],
                    "date": day,
                    "time": time,
                    "mode": mode,
                    "requirements": "Warm minimal living room. Keep the oak floor.",
                },
            )
            response.raise_for_status()
            appointment = response.json()
            if accept_as is not None:
                designer_token = login(client, accept_as, PASSWORD)
                client.post(
                    f"/appointments/{appointment['id']}/accept",
                    headers=auth(designer_token),
                ).raise_for_status()
            kind = "an in-person" if mode == "IN_PERSON" else "an online"
            print(f"booked {kind} consultation with {name} at {time}")

        # One open report, so the administrator has a queue to read.
        newest = client.get(
            "/projects/search", headers=auth(customer_token), params={"page_size": 1}
        ).json()["items"]
        if newest:
            reported = client.post(
                "/project-reports",
                headers=auth(customer_token),
                json={
                    "project_id": newest[0]["id"],
                    "reason": "Spam or misleading",
                    "comments": "This looks like a stock catalogue photo, not this studio's work.",
                },
            )
            reported.raise_for_status()
            print(f"reported one project: {newest[0]['title']}")


def auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def register(
    client: httpx.Client, email: str, password: str, display_name: str, role: str
) -> str:
    response = client.post(
        "/auth/register",
        json={
            "email": email,
            "password": password,
            "display_name": display_name,
            "role": role,
        },
    )
    response.raise_for_status()
    return response.json()["id"]


def login(client: httpx.Client, email: str, password: str) -> str:
    response = client.post("/auth/login", json={"email": email, "password": password})
    response.raise_for_status()
    return response.json()["access_token"]


PUBLIC = Path(__file__).resolve().parents[2] / "frontend" / "public"


def photo_tags(client: httpx.Client, token: str, image: str) -> list[str]:
    """Ask the analyser what the photo shows, the way a designer would.

    The tag search only works when the seeded projects speak the analyser's
    vocabulary, so the seed runs the same endpoint the editor calls.
    """
    path = PUBLIC / "portfolio" / "photos" / image
    if not path.is_file():
        return []
    response = client.post(
        "/images/tags",
        headers=auth(token),
        files={"file": (image, path.read_bytes(), "image/jpeg")},
        timeout=30.0,
    )
    if response.status_code != 200:
        return []
    return response.json().get("tags", [])


if __name__ == "__main__":
    main()