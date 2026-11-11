"""Write the running dataset to one JSON file.

The stores are in memory, so this file is the record of what a seeded backend
held: every account, company, project, category and quote request. It is not a
database backup — nothing reads it back into the app. ``seed_all.py`` rebuilds
the same content; this file lets a reader check that the rebuild matches, and
lets a reviewer see the data without starting anything.

Usage, with the backend running and seeded:

    APP_ADMIN_EMAIL=admin@example.com APP_ADMIN_PASSWORD=passw0rd123 \
        backend/.venv/Scripts/python.exe backend/scripts/export_snapshot.py

Writes ``testing/fixtures/video-environment.json``.
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path

import httpx

BASE = os.environ.get("DEMO_BASE", "http://127.0.0.1:8000/api")
ADMIN_EMAIL = os.environ.get("APP_ADMIN_EMAIL", "admin@example.com")
ADMIN_PASSWORD = os.environ.get("APP_ADMIN_PASSWORD", "passw0rd123")
PASSWORD = "passw0rd123"

TARGET = (
    Path(__file__).resolve().parents[2] / "testing" / "fixtures" / "video-environment.json"
)


def auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def login(client: httpx.Client, email: str, password: str = PASSWORD) -> str | None:
    response = client.post("/auth/login", json={"email": email, "password": password})
    if response.status_code != 200:
        return None
    return response.json()["access_token"]


def main() -> int:
    with httpx.Client(base_url=BASE, timeout=60) as client:
        admin = login(client, ADMIN_EMAIL, ADMIN_PASSWORD)
        if admin is None:
            print("Cannot sign in as the administrator. Check APP_ADMIN_EMAIL.")
            return 1

        accounts = client.get("/admin/accounts", headers=auth(admin)).json()
        companies = client.get("/companies", headers=auth(admin)).json()
        projects: list[dict] = []
        page = 1
        while True:
            chunk = client.get(
                "/projects/search",
                params={"page_size": 50, "page": page},
                headers=auth(admin),
            ).json()
            projects.extend(chunk["items"])
            if page >= chunk["pages"] or not chunk["items"]:
                break
            page += 1
        categories = client.get("/categories/all", headers=auth(admin)).json()

        # Every request is visible to the designer it was sent to.
        requests: dict[str, dict] = {}
        designers = [row for row in accounts if row["role"] == "DESIGNER"]
        for index, designer in enumerate(designers, start=1):
            token = login(client, designer["email"])
            if token is None:
                continue
            listing = client.get("/quotes/requests", headers=auth(token))
            if listing.status_code != 200:
                continue
            for row in listing.json():
                requests[row["id"]] = row
            if index % 10 == 0:
                print(f"designers read: {index} of {len(designers)}")

        snapshot = {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "backend": BASE,
            "password": PASSWORD,
            "counts": {
                "accounts": len(accounts),
                "companies": len(companies),
                "projects": len(projects),
                "categories": len(categories),
                "quote_requests": len(requests),
            },
            "accounts": accounts,
            "companies": companies,
            "projects": projects,
            "categories": categories,
            "quote_requests": sorted(requests.values(), key=lambda row: row["id"]),
        }

    TARGET.parent.mkdir(parents=True, exist_ok=True)
    TARGET.write_text(json.dumps(snapshot, indent=1), encoding="utf-8")
    print(f"wrote {TARGET}")
    print(json.dumps(snapshot["counts"], indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
