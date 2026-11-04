"""The search endpoint answers the customer filters."""

from __future__ import annotations

from typing import Any

from fastapi.testclient import TestClient

from app.api.deps import get_account_repository

CUSTOMER: dict[str, Any] = {
    "email": "casey@example.com",
    "password": "design4me",
    "display_name": "Casey",
    "role": "CUSTOMER",
}

PROJECTS = [
    {
        "title": "Warm Minimal Living Room",
        "style": "Minimal",
        "category": "Living Room",
        "budget_min": 20000,
        "budget_max": 40000,
    },
    {
        "title": "Cool Grey Study",
        "style": "Contemporary",
        "category": "Home Office",
        "budget_min": 60000,
        "budget_max": 90000,
    },
]


def sign_in(client: TestClient, account: dict[str, Any]) -> dict[str, str]:
    """Register, activate when needed, then sign in."""
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


def seed_catalogue(client: TestClient) -> dict[str, str]:
    """Publish two projects under one designer, then return the customer header."""
    designer = sign_in(
        client,
        {
            "email": "dana@example.com",
            "password": "design4me",
            "display_name": "Dana Studio",
            "role": "DESIGNER",
        },
    )
    client.post(
        "/api/companies",
        json={"name": "Studio Dana", "contact_email": "dana@example.com"},
        headers=designer,
    )
    for project in PROJECTS:
        response = client.post("/api/projects", json=project, headers=designer)
        assert response.status_code == 201, response.text
    return sign_in(client, CUSTOMER)


def test_search_requires_a_token(client: TestClient) -> None:
    assert client.get("/api/projects/search").status_code == 401


def test_an_empty_query_returns_the_catalogue(client: TestClient) -> None:
    headers = seed_catalogue(client)

    response = client.get("/api/projects/search", headers=headers)

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 2
    assert body["page"] == 1
    assert body["pages"] == 1
    assert len(body["items"]) == 2
    assert set(body) == {"items", "total", "page", "page_size", "pages"}


def test_keyword_narrows_the_result(client: TestClient) -> None:
    headers = seed_catalogue(client)

    response = client.get("/api/projects/search?keyword=warm", headers=headers)

    assert response.json()["total"] == 1
    assert response.json()["items"][0]["title"] == "Warm Minimal Living Room"


def test_category_narrows_the_result(client: TestClient) -> None:
    headers = seed_catalogue(client)

    response = client.get("/api/projects/search?category=Home%20Office", headers=headers)

    assert response.json()["total"] == 1
    assert response.json()["items"][0]["title"] == "Cool Grey Study"


def test_the_budget_range_excludes_expensive_projects(client: TestClient) -> None:
    headers = seed_catalogue(client)

    response = client.get("/api/projects/search?budget_max=50000", headers=headers)

    assert response.json()["total"] == 1
    assert response.json()["items"][0]["title"] == "Warm Minimal Living Room"


def test_paging_reports_the_page_count(client: TestClient) -> None:
    headers = seed_catalogue(client)

    response = client.get("/api/projects/search?page_size=1", headers=headers)

    body = response.json()
    assert body["pages"] == 2
    assert body["page_size"] == 1
    assert len(body["items"]) == 1


def test_a_page_below_one_returns_400(client: TestClient) -> None:
    headers = seed_catalogue(client)

    response = client.get("/api/projects/search?page=0", headers=headers)

    assert response.status_code == 400
    assert response.json()["detail"] == "Page must be 1 or higher"