"""Put the seeded store into the state the full tour expects.

Run after `seed_all.py`:

    DEMO_BASE=http://127.0.0.1:8010/api python testing/demo/prepare_tour.py

It clears Casey's shortlist, sends one quote request to Studio Verde, cancels
the seeded consultation with that studio, and registers one designer who is
left PENDING so the admin can approve somebody on camera.
"""

from __future__ import annotations

import os

import httpx

BASE = os.environ.get("DEMO_BASE", "http://127.0.0.1:8000/api")
PASSWORD = "passw0rd123"
WAITING_EMAIL = "waiting@example.com"


def main() -> int:
    client = httpx.Client(base_url=BASE, timeout=30)
    token = client.post(
        "/auth/login", json={"email": "casey@example.com", "password": PASSWORD}
    ).json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    saved = client.get("/shortlist", headers=headers).json()["project_ids"]
    for project_id in saved:
        client.delete(f"/shortlist/{project_id}", headers=headers)
    print(f"cleared {len(saved)} saved projects")

    companies = client.get("/companies", headers=headers).json()
    studio = next(row for row in companies if row["name"] == "Studio Verde")

    requests = client.get("/quotes/requests", headers=headers).json()
    open_requests = [
        row
        for row in requests
        if row["company_id"] == studio["id"] and row["state"] in ("PENDING", "ANSWERED")
    ]
    if not open_requests:
        created = client.post(
            "/quotes/requests",
            headers=headers,
            json={
                "company_id": studio["id"],
                "title": "Open plan kitchen and dining",
                "scope": "Remove one wall, rebuild the kitchen and fit new lighting.",
                "budget_min_cents": 3_000_000,
                "budget_max_cents": 5_000_000,
            },
        )
        print("created quote request", created.status_code)
    else:
        print(f"{len(open_requests)} open request(s) already with Studio Verde")

    appointments = client.get("/appointments", headers=headers).json()
    cancelled = 0
    for row in appointments:
        if row["company_id"] == studio["id"] and row["state"] != "CANCELLED":
            client.post(f"/appointments/{row['id']}/cancel", headers=headers)
            cancelled += 1
    print(f"cancelled {cancelled} open consultation(s) with Studio Verde")

    waiting = client.post(
        "/auth/register",
        json={
            "email": WAITING_EMAIL,
            "password": PASSWORD,
            "display_name": "Nadia Wong",
            "role": "DESIGNER",
        },
    )
    print("registered waiting designer", waiting.status_code)

    print("ready")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
