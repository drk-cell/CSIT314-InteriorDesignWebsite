"""Categories and reports: the platform staff features."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from fastapi.testclient import TestClient

from app.api.deps import (
    get_account_repository,
    get_project_repository,
    get_quote_request_repository,
    get_report_service,
)
from app.domain.account import Account
from app.domain.enums import Role
from app.domain.project import Project
from app.domain.quote_request import QuoteRequest

ADMIN: dict[str, Any] = {
    "email": "admin@example.com",
    "password": "passw0rd123",
    "display_name": "Admin",
    "role": "ADMIN",
}


def admin_headers(client: TestClient) -> dict[str, str]:
    """Put an administrator in the store, then sign in."""
    from app.api.deps import get_account_service

    get_account_service().ensure_staff_account(
        ADMIN["email"], ADMIN["password"], "Administrator", Role.ADMIN
    )
    response = client.post(
        "/api/auth/login",
        json={"email": ADMIN["email"], "password": ADMIN["password"]},
    )
    assert response.status_code == 200, response.text
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def customer_headers(client: TestClient) -> dict[str, str]:
    client.post(
        "/api/auth/register",
        json={
            "email": "casey@example.com",
            "password": "design4me",
            "display_name": "Casey",
            "role": "CUSTOMER",
        },
    )
    stored = get_account_repository().get_by_email("casey@example.com")
    if stored is not None and not stored.can_login():
        stored.activate()
    response = client.post(
        "/api/auth/login",
        json={"email": "casey@example.com", "password": "design4me"},
    )
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


# --- categories -----------------------------------------------------------


def test_the_public_list_needs_no_token(client: TestClient) -> None:
    response = client.get("/api/categories")

    assert response.status_code == 200
    assert len(response.json()) == 10


def test_staff_add_a_category(client: TestClient) -> None:
    headers = admin_headers(client)

    created = client.post("/api/categories", json={"name": "Rooftop"}, headers=headers)
    listing = client.get("/api/categories")

    assert created.status_code == 201
    assert "Rooftop" in [entry["name"] for entry in listing.json()]


def test_a_repeated_name_is_refused(client: TestClient) -> None:
    headers = admin_headers(client)

    first = client.post("/api/categories", json={"name": "Rooftop"}, headers=headers)
    second = client.post("/api/categories", json={"name": "rooftop"}, headers=headers)

    assert first.status_code == 201
    assert second.status_code == 409


def test_a_customer_cannot_add_a_category(client: TestClient) -> None:
    headers = customer_headers(client)

    response = client.post("/api/categories", json={"name": "Rooftop"}, headers=headers)

    assert response.status_code == 403


def test_archiving_hides_the_category_from_the_public_list(client: TestClient) -> None:
    headers = admin_headers(client)
    created = client.post("/api/categories", json={"name": "Rooftop"}, headers=headers).json()

    archived = client.patch(
        f"/api/categories/{created['id']}", json={"active": False}, headers=headers
    )
    public = client.get("/api/categories")
    staff = client.get("/api/categories/all", headers=headers)

    assert archived.status_code == 200
    assert "Rooftop" not in [entry["name"] for entry in public.json()]
    assert "Rooftop" in [entry["name"] for entry in staff.json()]


def test_renaming_a_category_updates_the_catalogue(client: TestClient) -> None:
    headers = admin_headers(client)
    created = client.post("/api/categories", json={"name": "Rooftop"}, headers=headers).json()

    client.patch(
        f"/api/categories/{created['id']}", json={"name": "Roof Terrace"}, headers=headers
    )
    catalogue = client.get("/api/catalogue").json()

    assert "Roof Terrace" in catalogue["categories"]
    assert "Rooftop" not in catalogue["categories"]


# --- reports --------------------------------------------------------------


def test_a_report_needs_staff(client: TestClient) -> None:
    headers = customer_headers(client)

    response = client.get("/api/reports?period=daily", headers=headers)

    assert response.status_code == 403


def test_a_daily_report_returns_the_requested_buckets(client: TestClient) -> None:
    headers = admin_headers(client)

    response = client.get("/api/reports?period=daily&buckets=7", headers=headers)

    assert response.status_code == 200
    body = response.json()
    assert body["period"] == "daily"
    assert len(body["buckets"]) == 7
    assert body["buckets"][-1]["label"] == datetime.now(timezone.utc).strftime("%Y-%m-%d")


def test_the_last_bucket_counts_today(client: TestClient) -> None:
    accounts = get_account_repository()
    project_repository = get_project_repository()
    requests = get_quote_request_repository()
    accounts.add(
        Account(
            email="fresh@example.com",
            password_hash="x",
            display_name="Fresh",
            role=Role.CUSTOMER,
        )
    )
    project_repository.add(Project(owner_id="o", company_id="c", title="Today"))
    requests.add(
        QuoteRequest(
            customer_id="c",
            company_id="co",
            title="Today",
            scope="Scope",
        )
    )

    report = get_report_service().build(period="daily", buckets=3)

    assert report.buckets[-1].accounts == 1
    assert report.buckets[-1].projects == 1
    assert report.buckets[-1].quote_requests == 1


def test_an_old_record_lands_in_its_own_bucket() -> None:
    repository = get_project_repository()
    old = Project(owner_id="o", company_id="c", title="Old")
    old.created_at = datetime.now(timezone.utc) - timedelta(days=3)
    repository.add(old)

    report = get_report_service().build(period="daily", buckets=7)
    by_label = {bucket.label: bucket.projects for bucket in report.buckets}

    assert sum(by_label.values()) == 1
    assert by_label[report.buckets[-1].label] == 0


def test_a_weekly_report_labels_iso_weeks(client: TestClient) -> None:
    headers = admin_headers(client)

    body = client.get("/api/reports?period=weekly&buckets=4", headers=headers).json()

    assert len(body["buckets"]) == 4
    assert all("-W" in bucket["label"] for bucket in body["buckets"])


def test_a_monthly_report_labels_months(client: TestClient) -> None:
    headers = admin_headers(client)

    body = client.get("/api/reports?period=monthly&buckets=3", headers=headers).json()

    assert len(body["buckets"]) == 3
    assert all(len(bucket["label"]) == 7 for bucket in body["buckets"])


def test_an_unknown_period_is_refused(client: TestClient) -> None:
    headers = admin_headers(client)

    response = client.get("/api/reports?period=yearly", headers=headers)

    assert response.status_code == 400