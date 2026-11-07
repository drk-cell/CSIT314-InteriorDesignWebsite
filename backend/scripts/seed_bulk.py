"""Generate the test data the brief asks for: 100 records of each type.

Creates twenty designers with companies, one hundred customers, one hundred
projects, one hundred quote requests and one hundred answered quotes. It talks
to a running backend over HTTP, so it needs the server up and the admin
credentials in the environment.

Run once against a fresh server:

    APP_ADMIN_EMAIL=admin@example.com APP_ADMIN_PASSWORD=passw0rd123 \
        python scripts/seed_bulk.py

The script stops early when the first generated account already exists, so a
second run does not duplicate the data.
"""

from __future__ import annotations

import os

import httpx

BASE = os.environ.get("DEMO_BASE", "http://127.0.0.1:8000/api")
ADMIN_EMAIL = os.environ.get("APP_ADMIN_EMAIL", "admin@example.com")
ADMIN_PASSWORD = os.environ.get("APP_ADMIN_PASSWORD", "change-me")
PASSWORD = "passw0rd123"

DESIGNERS = 20
CUSTOMERS = 100
PROJECTS = 100
REQUESTS = 100
PHOTOS = [f"/portfolio/photos/photo-{index:02d}.jpg" for index in range(1, 17)]


def auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def login(client: httpx.Client, email: str, password: str = PASSWORD) -> str:
    response = client.post("/auth/login", json={"email": email, "password": password})
    response.raise_for_status()
    return response.json()["access_token"]


def register(
    client: httpx.Client, email: str, name: str, role: str
) -> str | None:
    """Register an account. Returns its id, or None when it already exists."""
    response = client.post(
        "/auth/register",
        json={"email": email, "password": PASSWORD, "display_name": name, "role": role},
    )
    if response.status_code == 409:
        return None
    response.raise_for_status()
    return response.json()["id"]


def main() -> None:
    with httpx.Client(base_url=BASE, timeout=60) as client:
        admin = login(client, ADMIN_EMAIL, ADMIN_PASSWORD)
        catalogue = client.get("/catalogue").json()
        categories = catalogue["categories"]
        styles = catalogue["styles"]

        first = register(client, "designer000@example.com", "Studio 000", "DESIGNER")
        if first is None:
            print("bulk data already present; nothing to do")
            return
        client.post(f"/admin/accounts/{first}/approve", headers=auth(admin))

        designers: list[tuple[str, str]] = []
        for index in range(DESIGNERS):
            email = f"designer{index:03d}@example.com"
            if index > 0:
                account_id = register(client, email, f"Studio {index:03d}", "DESIGNER")
                assert account_id is not None
                client.post(f"/admin/accounts/{account_id}/approve", headers=auth(admin))
            token = login(client, email)
            company = client.post(
                "/companies",
                headers=auth(token),
                json={
                    "name": f"Studio {index:03d}",
                    "description": "Residential interiors, measured drawings and build.",
                    "contact_email": f"hello{index:03d}@studio{index:03d}.sg",
                    "contact_phone": f"+65 6000 {index:04d}",
                    "location": "Singapore" if index % 2 == 0 else "Kuala Lumpur",
                },
            )
            company.raise_for_status()
            designers.append((token, company.json()["id"]))
        print(f"designers: {len(designers)}")

        customers: list[str] = []
        for index in range(CUSTOMERS):
            email = f"customer{index:03d}@example.com"
            register(client, email, f"Customer {index:03d}", "CUSTOMER")
            customers.append(login(client, email))
        print(f"customers: {len(customers)}")

        for index in range(PROJECTS):
            token, _ = designers[index % DESIGNERS]
            response = client.post(
                "/projects",
                headers=auth(token),
                json={
                    "title": f"Project {index:03d} {categories[index % len(categories)]}",
                    "description": "Layout, joinery and lighting reworked for daily use.",
                    "category": categories[index % len(categories)],
                    "style": styles[index % len(styles)],
                    "budget_min": 15_000 + index * 500,
                    "budget_max": 45_000 + index * 900,
                    "images": [PHOTOS[index % len(PHOTOS)]],
                    "tags": ["warm palette", styles[index % len(styles)].lower()],
                },
            )
            response.raise_for_status()
        print(f"projects: {PROJECTS}")

        created: list[tuple[str, str, str]] = []
        for index in range(REQUESTS):
            token, company_id = designers[index % DESIGNERS]
            response = client.post(
                "/quotes/requests",
                headers=auth(customers[index]),
                json={
                    "company_id": company_id,
                    "title": f"Quotation {index:03d}",
                    "scope": "Whole flat, four rooms, move-in by next quarter.",
                    "budget_min_cents": (20_000 + index * 100) * 100,
                    "budget_max_cents": (45_000 + index * 150) * 100,
                    "target_cents": (30_000 + index * 120) * 100,
                },
            )
            response.raise_for_status()
            body = response.json()
            created.append((token, body["id"], body["id"]))
        print(f"quote requests: {len(created)}")

        for index, (token, request_id, _) in enumerate(created):
            response = client.post(
                f"/quotes/requests/{request_id}/quotes",
                headers=auth(token),
                json={
                    "total_cents": (28_000 + index * 130) * 100,
                    "valid_days": 14,
                    "gst_included": index % 2 == 0,
                    "note": "Includes carpentry, electrical and painting.",
                },
            )
            response.raise_for_status()
        print(f"quotes: {len(created)}")

        summary = client.get("/reports?period=monthly&buckets=3", headers=auth(admin)).json()
        latest = summary["buckets"][-1]
        print(
            "this month: "
            f"{latest['accounts']} accounts, {latest['projects']} projects, "
            f"{latest['quote_requests']} requests, {latest['quotes']} quotes"
        )


if __name__ == "__main__":
    main()