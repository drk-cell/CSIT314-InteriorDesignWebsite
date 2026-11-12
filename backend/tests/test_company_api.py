"""The company endpoints honour the published contract."""

from __future__ import annotations

from typing import Any

from fastapi.testclient import TestClient

from app.api.deps import get_account_repository

DESIGNER: dict[str, Any] = {
    "email": "dana@example.com",
    "password": "design4me",
    "display_name": "Dana Studio",
    "role": "DESIGNER",
}

CUSTOMER: dict[str, Any] = {
    "email": "casey@example.com",
    "password": "design4me",
    "display_name": "Casey",
    "role": "CUSTOMER",
}

COMPANY: dict[str, Any] = {
    "name": "Studio Verde",
    "description": "Warm minimal interiors.",
    "contact_email": "hello@verde.sg",
    "contact_phone": "+65 6123 4567",
    "location": "Singapore",
}


def sign_in(client: TestClient, account: dict[str, Any]) -> dict[str, str]:
    """Register the account, approve it if needed, then sign in.

    The approval flow has its own suite. Here the designer is activated
    directly so the company tests do not repeat that setup.
    """
    client.post("/api/auth/register", json=account)
    stored = get_account_repository().get_by_email(account["email"])
    if stored is not None and not stored.can_login():
        stored.activate()
    response = client.post(
        "/api/auth/login",
        json={"email": account["email"], "password": account["password"]},
    )
    assert response.status_code == 200, response.text
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def test_a_designer_creates_a_profile(client: TestClient) -> None:
    headers = sign_in(client, DESIGNER)

    response = client.post("/api/companies", json=COMPANY, headers=headers)

    assert response.status_code == 201
    body = response.json()
    assert body["name"] == "Studio Verde"
    assert body["contact_email"] == "hello@verde.sg"
    assert body["owner_id"]
    assert set(body) == {
        "id",
        "owner_id",
        "name",
        "description",
        "contact_email",
        "contact_phone",
        "location",
        "meeting_address",
        "call_link",
        "logo_url",
        "created_at",
        "updated_at",
    }


def test_a_customer_cannot_create_a_profile(client: TestClient) -> None:
    headers = sign_in(client, CUSTOMER)

    response = client.post("/api/companies", json=COMPANY, headers=headers)

    assert response.status_code == 403


def test_a_second_profile_returns_409(client: TestClient) -> None:
    headers = sign_in(client, DESIGNER)
    client.post("/api/companies", json=COMPANY, headers=headers)

    response = client.post("/api/companies", json=COMPANY, headers=headers)

    assert response.status_code == 409
    assert response.json()["detail"] == "This designer already has a company profile"


def test_reading_my_profile_before_creating_one_returns_404(
    client: TestClient,
) -> None:
    headers = sign_in(client, DESIGNER)

    response = client.get("/api/companies/me", headers=headers)

    assert response.status_code == 404


def test_the_owner_updates_one_field(client: TestClient) -> None:
    headers = sign_in(client, DESIGNER)
    client.post("/api/companies", json=COMPANY, headers=headers)

    response = client.patch("/api/companies/me", json={"name": "Verde Studio"}, headers=headers)

    assert response.status_code == 200
    assert response.json()["name"] == "Verde Studio"
    assert response.json()["location"] == "Singapore"


def test_the_owner_cannot_save_a_blank_name(client: TestClient) -> None:
    headers = sign_in(client, DESIGNER)
    client.post("/api/companies", json=COMPANY, headers=headers)

    response = client.patch("/api/companies/me", json={"name": "   "}, headers=headers)

    assert response.status_code == 400
    assert response.json()["detail"] == "Company name must not be empty"


def test_another_account_reads_a_profile_by_id(client: TestClient) -> None:
    owner_headers = sign_in(client, DESIGNER)
    created = client.post("/api/companies", json=COMPANY, headers=owner_headers).json()
    shopper_headers = sign_in(client, CUSTOMER)

    response = client.get(f"/api/companies/{created['id']}", headers=shopper_headers)

    assert response.status_code == 200
    assert response.json()["name"] == "Studio Verde"


def test_an_unknown_company_returns_404(client: TestClient) -> None:
    headers = sign_in(client, CUSTOMER)

    response = client.get("/api/companies/does-not-exist", headers=headers)

    assert response.status_code == 404


def test_the_endpoints_require_a_token(client: TestClient) -> None:
    assert client.get("/api/companies/me").status_code == 401
    assert client.post("/api/companies", json=COMPANY).status_code == 401

def test_listing_requires_a_token(client: TestClient) -> None:
    assert client.get("/api/companies").status_code == 401


def test_a_customer_lists_the_published_profiles(client: TestClient) -> None:
    owner_headers = sign_in(client, DESIGNER)
    client.post("/api/companies", json=COMPANY, headers=owner_headers)
    shopper_headers = sign_in(client, CUSTOMER)

    response = client.get("/api/companies", headers=shopper_headers)

    assert response.status_code == 200
    assert [row["name"] for row in response.json()] == ["Studio Verde"]


def test_the_listing_is_sorted_by_name(client: TestClient) -> None:
    zed = sign_in(client, {**DESIGNER, "email": "zed@example.com", "display_name": "Zed"})
    amy = sign_in(client, {**DESIGNER, "email": "amy@example.com", "display_name": "Amy"})
    client.post("/api/companies", json={**COMPANY, "name": "Zed Atelier"}, headers=zed)
    client.post("/api/companies", json={**COMPANY, "name": "Amy Interiors"}, headers=amy)
    shopper_headers = sign_in(client, CUSTOMER)

    response = client.get("/api/companies", headers=shopper_headers)

    assert [row["name"] for row in response.json()] == ["Amy Interiors", "Zed Atelier"]
