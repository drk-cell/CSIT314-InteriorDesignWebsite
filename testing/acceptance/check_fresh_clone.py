"""Check a fresh clone end to end: the API on :8000 and the dev server on :5173.

Run it after `seed_all.py`, on a machine that cloned the repository:

    APP_ADMIN_EMAIL=admin@example.com APP_ADMIN_PASSWORD=passw0rd123 \
        backend/.venv/Scripts/python.exe backend/scripts/seed_all.py
    backend/.venv/Scripts/python.exe testing/acceptance/check_fresh_clone.py

It compares the live counts with testing/fixtures/video-environment.json, then
walks the three roles through one full journey each. Exit code 0 means every
check passed. Set API_BASE and WEB_BASE to use other ports.
"""

from __future__ import annotations

import io
import json
import os
import sys
import time
from pathlib import Path

import httpx
from PIL import Image

API = os.environ.get("API_BASE", "http://127.0.0.1:8000/api")
WEB = os.environ.get("WEB_BASE", "http://127.0.0.1:5173")
PASSWORD = "passw0rd123"
ROOT = Path(__file__).resolve().parents[2]
FIXTURE = json.loads((ROOT / "testing/fixtures/video-environment.json").read_text(encoding="utf-8"))

results: list[tuple[bool, str, str]] = []


def check(name: str, ok: bool, detail: str = "") -> None:
    results.append((ok, name, detail))
    print(("PASS  " if ok else "FAIL  ") + name + (f"  [{detail}]" if detail else ""))


c = httpx.Client(base_url=API, timeout=120)


def token(email: str) -> str:
    return c.post("/auth/login", json={"email": email, "password": PASSWORD}).json()["access_token"]


def main() -> int:
    check("health", c.get("/health").status_code == 200)

    tokens: dict[str, str] = {}
    for role, email in [("admin", "admin@example.com"), ("customer", "casey@example.com"),
                        ("designer", "verde@example.com")]:
        response = c.post("/auth/login", json={"email": email, "password": PASSWORD})
        ok = response.status_code == 200
        if ok:
            tokens[role] = response.json()["access_token"]
            ok = response.json()["account"]["role"] in ("ADMIN", "PLATFORM_MANAGER", "CUSTOMER", "DESIGNER")
        check(f"sign in {role} ({email})", ok, str(response.status_code))

    if len(tokens) != 3:
        return 1

    admin = {"Authorization": f"Bearer {tokens['admin']}"}
    customer = {"Authorization": f"Bearer {tokens['customer']}"}
    designer = {"Authorization": f"Bearer {tokens['designer']}"}

    accounts = c.get("/admin/accounts", headers=admin)
    rows = accounts.json() if accounts.status_code == 200 else []
    check("accounts match the fixture", len(rows) == len(FIXTURE["accounts"]),
          f"{len(rows)} live, {len(FIXTURE['accounts'])} in fixture")

    companies = c.get("/companies", headers=customer).json()
    check("companies match the fixture", len(companies) == len(FIXTURE["companies"]),
          f"{len(companies)} live, {len(FIXTURE['companies'])} in fixture")

    catalogue = c.get("/catalogue", headers=customer).json()
    check("categories match the fixture", len(catalogue["categories"]) == len(FIXTURE["categories"]),
          f"{len(catalogue['categories'])} categories, {len(catalogue['styles'])} styles")

    search = c.get("/projects/search", headers=customer).json()
    check("projects match the fixture", search["total"] == len(FIXTURE["projects"]),
          f"{search['total']} live, {len(FIXTURE['projects'])} in fixture")

    tagged = c.get("/projects/search", headers=customer, params={"tags": "sofa"}).json()
    check("tag search returns hits", tagged["total"] > 0, f"{tagged['total']} hits for 'sofa'")

    # Seeded projects point at the 16 photos in frontend/public/portfolio/photos.
    urls, missing = [], []
    for row in search["items"]:
        for url in row.get("images") or []:
            if url.startswith("/portfolio/"):
                urls.append(url)
    for url in dict.fromkeys(urls):
        response = httpx.get(WEB + url, timeout=60)
        if response.status_code != 200 or not response.content:
            missing.append(url)
    check("project photos load in the browser", bool(urls) and not missing,
          f"{len(set(urls))} photos checked, missing {missing[:3]}")

    on_disk = sorted((ROOT / "frontend/public/portfolio/photos").glob("*.jpg"))
    check("all 16 demo photos are in the clone", len(on_disk) == 16, f"{len(on_disk)} files")

    mine = c.get("/projects/mine", headers=designer)
    check("designer sees own projects", mine.status_code == 200 and len(mine.json()) == 3,
          f"{len(mine.json())} projects")

    report = c.get("/reports", headers=admin)
    body = report.json() if report.status_code == 200 else {}
    check("report builds", report.status_code == 200 and len(body.get("buckets", [])) > 0,
          f"{len(body.get('buckets', []))} buckets")

    # Quote flow from scratch, aimed at the designer who must answer it.
    company_id = c.get("/companies/me", headers=designer).json()["id"]
    created = c.post("/quotes/requests", headers=customer,
                     json={"company_id": company_id, "title": "Fresh clone check",
                           "scope": "Whole kitchen, 12 square metres.", "budget_min_cents": 100000,
                           "budget_max_cents": 500000})
    check("customer sends a request", created.status_code in (200, 201), str(created.status_code))
    request_id = created.json().get("id") if created.status_code in (200, 201) else None
    if request_id:
        inbox = c.get("/quotes/requests", headers=designer).json()
        check("request reaches the designer inbox", any(str(row.get("id")) == str(request_id) for row in inbox),
              f"{len(inbox)} in inbox")
        answered = c.post(f"/quotes/requests/{request_id}/quotes", headers=designer,
                          json={"total_cents": 420000, "valid_days": 21, "note": "Fresh clone quote"})
        check("designer answers the request", answered.status_code in (200, 201), str(answered.status_code))
        quote = answered.json() if answered.status_code in (200, 201) else {}
        quote_id = quote.get("id") or (quote.get("quote") or {}).get("id")
        if quote_id:
            accepted = c.post(f"/quotes/{quote_id}/accept", headers=customer)
            check("customer accepts the quote", accepted.status_code in (200, 204), str(accepted.status_code))
        else:
            check("customer accepts the quote", False, f"no quote id: {str(quote)[:80]}")

    # Shortlist.
    seeded_saved = c.get("/shortlist", headers=customer).json()
    check("seeded shortlist has 3 projects", len(seeded_saved["items"]) == 3,
          f"{len(seeded_saved['items'])} saved at seed time")

    saved = seeded_saved["project_ids"]
    before = len(saved)
    project_id = next(row["id"] for row in search["items"] if row["id"] not in saved)
    add = c.post(f"/shortlist/{project_id}", headers=customer)
    listing = c.get("/shortlist", headers=customer).json()
    check("shortlist add + list", add.status_code in (200, 201, 204) and len(listing["items"]) == before + 1,
          f"add {add.status_code}, {before} -> {len(listing['items'])} saved")
    removed = c.delete(f"/shortlist/{project_id}", headers=customer)
    check("shortlist remove", removed.status_code in (200, 204), str(removed.status_code))

    # Approval gate for a new designer.
    email = f"freshclone{int(time.time())}@example.com"
    registered = c.post("/auth/register", json={"email": email, "password": PASSWORD,
                                                "display_name": "Fresh Clone", "role": "DESIGNER"})
    check("register a new designer", registered.status_code in (200, 201), str(registered.status_code))
    if registered.status_code in (200, 201):
        blocked = c.post("/auth/login", json={"email": email, "password": PASSWORD})
        check("new designer waits for approval", blocked.status_code in (401, 403), str(blocked.status_code))
        body = registered.json()
        new_id = (body.get("account") or body)["id"]
        approved = c.post(f"/admin/accounts/{new_id}/approve", headers=admin)
        check("admin approves the designer", approved.status_code == 200, str(approved.status_code))
        allowed = c.post("/auth/login", json={"email": email, "password": PASSWORD})
        check("approved designer signs in", allowed.status_code == 200, str(allowed.status_code))

    # Uploads on a clone that has no uploads folder yet.
    buffer = io.BytesIO()
    Image.new("RGB", (640, 480), (180, 120, 90)).save(buffer, format="JPEG")
    photo = buffer.getvalue()
    upload = c.post("/images", headers=designer, files={"file": ("clone.jpg", photo, "image/jpeg")})
    check("upload a photo", upload.status_code in (200, 201), str(upload.status_code))
    if upload.status_code in (200, 201):
        url = upload.json()["url"]
        served = httpx.get("http://127.0.0.1:8000" + url, timeout=60)
        check("upload served by the API", served.status_code == 200, f"{url} -> {served.status_code}")
        via_web = httpx.get(WEB + url, timeout=60)
        check("upload served through the dev proxy", via_web.status_code == 200,
              f"{via_web.status_code}, {len(via_web.content)} bytes")

    analysed = c.post("/images/tags", headers=designer, files={"file": ("clone.jpg", photo, "image/jpeg")})
    body = analysed.json() if analysed.status_code == 200 else {}
    check("photo analyser returns tags", analysed.status_code == 200 and bool(body.get("tags")),
          f"{len(body.get('tags', []))} tags, engine {body.get('engine')}")

    passed = sum(1 for ok, _, _ in results if ok)
    print(f"\n{passed}/{len(results)} checks passed")
    return 0 if passed == len(results) else 2


if __name__ == "__main__":
    sys.exit(main())
