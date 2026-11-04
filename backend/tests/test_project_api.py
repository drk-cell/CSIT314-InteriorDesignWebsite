"""The project endpoints honour the published contract."""

from __future__ import annotations

from typing import Any

from fastapi.testclient import TestClient

from app.api.deps import get_account_repository

PROJECT: dict[str, Any] = {
    "title": "Warm Minimal Living Room",
    "description": "A compact flat opened up.",
    "style": "Minimal",
    "category": "Living Room",
    "budget_min": 20000,
    "budget_max": 40000,
    "images": ["/portfolio/photos/photo-01.jpg"],
}


def sign_in(client: TestClient, account: dict[str, Any]) -> dict[str, str]:
    """Register, activate when needed, then sign in and return the header."""
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


def designer_with_company(client: TestClient, email: str) -> dict[str, str]:
    """A signed in designer who holds a company."""
    headers = sign_in(
        client,
        {
            "email": email,
            "password": "design4me",
            "display_name": "Dana Studio",
            "role": "DESIGNER",
        },
    )
    response = client.post(
        "/api/companies",
        json={
            "name": f"Studio {email.split('@')[0]}",
            "contact_email": email,
            "contact_phone": "",
            "location": "Singapore",
        },
        headers=headers,
    )
    assert response.status_code == 201, response.text
    return headers


def test_create_requires_a_token(client: TestClient) -> None:
    assert client.post("/api/projects", json=PROJECT).status_code == 401


def test_a_customer_cannot_publish(client: TestClient) -> None:
    headers = sign_in(
        client,
        {
            "email": "casey@example.com",
            "password": "design4me",
            "display_name": "Casey",
            "role": "CUSTOMER",
        },
    )

    response = client.post("/api/projects", json=PROJECT, headers=headers)

    assert response.status_code == 403


def test_a_designer_without_a_company_gets_403(client: TestClient) -> None:
    headers = sign_in(
        client,
        {
            "email": "dana@example.com",
            "password": "design4me",
            "display_name": "Dana",
            "role": "DESIGNER",
        },
    )

    response = client.post("/api/projects", json=PROJECT, headers=headers)

    assert response.status_code == 403
    assert response.json()["detail"] == "Company profile not found"


def test_publish_returns_the_public_shape(client: TestClient) -> None:
    headers = designer_with_company(client, "dana@example.com")

    response = client.post("/api/projects", json=PROJECT, headers=headers)

    assert response.status_code == 201
    body = response.json()
    assert body["title"] == "Warm Minimal Living Room"
    assert body["status"] == "CURRENT"
    assert body["view_count"] == 0
    assert body["shortlist_count"] == 0
    assert body["images"] == ["/portfolio/photos/photo-01.jpg"]
    assert set(body) == {
        "id",
        "owner_id",
        "company_id",
        "title",
        "description",
        "style",
        "category",
        "budget_min",
        "budget_max",
        "status",
        "images",
        "view_count",
        "shortlist_count",
        "created_at",
        "updated_at",
    }


def test_another_account_reads_the_project(client: TestClient) -> None:
    owner_headers = designer_with_company(client, "dana@example.com")
    created = client.post("/api/projects", json=PROJECT, headers=owner_headers).json()
    shopper_headers = sign_in(
        client,
        {
            "email": "casey@example.com",
            "password": "design4me",
            "display_name": "Casey",
            "role": "CUSTOMER",
        },
    )

    response = client.get(f"/api/projects/{created['id']}", headers=shopper_headers)

    assert response.status_code == 200
    assert response.json()["title"] == "Warm Minimal Living Room"


def test_the_owner_updates_one_field(client: TestClient) -> None:
    headers = designer_with_company(client, "dana@example.com")
    created = client.post("/api/projects", json=PROJECT, headers=headers).json()

    response = client.patch(
        f"/api/projects/{created['id']}",
        json={"title": "Quiet Living Room"},
        headers=headers,
    )

    assert response.status_code == 200
    assert response.json()["title"] == "Quiet Living Room"
    assert response.json()["category"] == "Living Room"


def test_another_designer_cannot_update(client: TestClient) -> None:
    owner_headers = designer_with_company(client, "dana@example.com")
    stranger_headers = designer_with_company(client, "other@example.com")
    created = client.post("/api/projects", json=PROJECT, headers=owner_headers).json()

    response = client.patch(
        f"/api/projects/{created['id']}",
        json={"title": "Hijacked"},
        headers=stranger_headers,
    )

    assert response.status_code == 403


def test_delete_removes_the_project(client: TestClient) -> None:
    headers = designer_with_company(client, "dana@example.com")
    created = client.post("/api/projects", json=PROJECT, headers=headers).json()

    removed = client.delete(f"/api/projects/{created['id']}", headers=headers)
    missing = client.get(f"/api/projects/{created['id']}", headers=headers)

    assert removed.status_code == 204
    assert missing.status_code == 404


def test_mine_filters_by_status(client: TestClient) -> None:
    headers = designer_with_company(client, "dana@example.com")
    first = client.post("/api/projects", json=PROJECT, headers=headers).json()
    second = client.post(
        "/api/projects", json={**PROJECT, "title": "Past Bedroom"}, headers=headers
    ).json()
    client.patch(
        f"/api/projects/{second['id']}", json={"status": "PAST"}, headers=headers
    )

    response = client.get("/api/projects/mine?status=CURRENT", headers=headers)

    assert response.status_code == 200
    assert [entry["id"] for entry in response.json()] == [first["id"]]


def test_the_company_portfolio_is_public(client: TestClient) -> None:
    owner_headers = designer_with_company(client, "dana@example.com")
    created = client.post("/api/projects", json=PROJECT, headers=owner_headers).json()
    shopper_headers = sign_in(
        client,
        {
            "email": "casey@example.com",
            "password": "design4me",
            "display_name": "Casey",
            "role": "CUSTOMER",
        },
    )

    response = client.get(
        f"/api/projects/company/{created['company_id']}", headers=shopper_headers
    )

    assert response.status_code == 200
    assert [entry["id"] for entry in response.json()] == [created["id"]]


def test_nine_images_are_rejected(client: TestClient) -> None:
    headers = designer_with_company(client, "dana@example.com")
    payload = {**PROJECT, "images": [f"/x/{i}.jpg" for i in range(9)]}

    response = client.post("/api/projects", json=payload, headers=headers)

    assert response.status_code == 422