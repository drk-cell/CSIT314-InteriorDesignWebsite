"""Shortlist: entity rules, the service, and the endpoints."""

from __future__ import annotations

from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.api.deps import get_account_repository
from app.domain.shortlist import MAX_ENTRIES, Shortlist
from app.services.shortlist_service import ShortlistService


def test_a_saved_project_is_listed_once() -> None:
    shortlist = Shortlist(customer_id="casey")

    assert shortlist.add("project-1") is True
    assert shortlist.add("project-1") is False
    assert shortlist.project_ids == ["project-1"]


def test_removing_an_absent_project_changes_nothing() -> None:
    shortlist = Shortlist(customer_id="casey", project_ids=["a"])

    assert shortlist.remove("b") is False
    assert shortlist.project_ids == ["a"]


def test_the_list_is_bounded() -> None:
    shortlist = Shortlist(customer_id="casey")

    with pytest.raises(ValueError):
        Shortlist(customer_id="casey", project_ids=[f"p{i}" for i in range(MAX_ENTRIES + 1)])


# --- endpoints -------------------------------------------------------------


def sign_in(client: TestClient, account: dict[str, Any]) -> dict[str, str]:
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


def customer(client: TestClient, email: str = "casey@example.com") -> dict[str, str]:
    return sign_in(
        client,
        {
            "email": email,
            "password": "design4me",
            "display_name": "Casey",
            "role": "CUSTOMER",
        },
    )


def designer(client: TestClient, email: str = "dana@example.com") -> dict[str, str]:
    headers = sign_in(
        client,
        {
            "email": email,
            "password": "design4me",
            "display_name": "Dana",
            "role": "DESIGNER",
        },
    )
    client.post(
        "/api/companies",
        json={"name": f"Studio {email}", "contact_email": email},
        headers=headers,
    )
    return headers


def publish(client: TestClient, headers: dict[str, str], title: str = "Warm Room") -> dict[str, Any]:
    response = client.post(
        "/api/projects",
        json={
            "title": title,
            "style": "Minimal",
            "category": "Living Room",
            "budget_min": 20000,
            "budget_max": 40000,
        },
        headers=headers,
    )
    assert response.status_code == 201, response.text
    return response.json()


def test_a_customer_saves_one_project(client: TestClient) -> None:
    project = publish(client, designer(client))
    shopper = customer(client)

    response = client.post(f"/api/shortlist/{project['id']}", headers=shopper)
    listing = client.get("/api/shortlist", headers=shopper)

    assert response.status_code == 201
    assert listing.json()["project_ids"] == [project["id"]]


def test_saving_twice_counts_once(client: TestClient) -> None:
    owner = designer(client)
    project = publish(client, owner)
    shopper = customer(client)

    client.post(f"/api/shortlist/{project['id']}", headers=shopper)
    client.post(f"/api/shortlist/{project['id']}", headers=shopper)

    detail = client.get(f"/api/projects/{project['id']}", headers=shopper).json()
    assert detail["shortlist_count"] == 1


def test_removing_lowers_the_counter(client: TestClient) -> None:
    project = publish(client, designer(client))
    shopper = customer(client)

    client.post(f"/api/shortlist/{project['id']}", headers=shopper)
    second = client.delete(f"/api/shortlist/{project['id']}", headers=shopper)
    detail = client.get(f"/api/projects/{project['id']}", headers=shopper).json()

    assert second.status_code == 204
    assert detail["shortlist_count"] == 0


def test_the_saved_list_returns_projects(client: TestClient) -> None:
    owner = designer(client)
    first = publish(client, owner, "Warm Room")
    second = publish(client, owner, "Cool Room")
    shopper = customer(client)

    client.post(f"/api/shortlist/{first['id']}", headers=shopper)
    client.post(f"/api/shortlist/{second['id']}", headers=shopper)

    listing = client.get("/api/shortlist", headers=shopper)

    assert [entry["title"] for entry in listing.json()["items"]] == ["Warm Room", "Cool Room"]


def test_a_designer_cannot_save(client: TestClient) -> None:
    owner = designer(client)
    project = publish(client, owner)
    other = designer(client, "other@example.com")

    response = client.post(f"/api/shortlist/{project['id']}", headers=other)

    assert response.status_code == 403


def test_saving_an_unknown_project_is_404(client: TestClient) -> None:
    shopper = customer(client)

    response = client.post("/api/shortlist/does-not-exist", headers=shopper)

    assert response.status_code == 404


def test_a_view_is_counted(client: TestClient) -> None:
    project = publish(client, designer(client))
    shopper = customer(client)

    counted = client.post(f"/api/projects/{project['id']}/view", headers=shopper)
    detail = client.get(f"/api/projects/{project['id']}", headers=shopper).json()

    assert counted.status_code == 204
    assert detail["view_count"] == 1


def test_an_empty_shortlist_is_an_empty_list(client: TestClient) -> None:
    shopper = customer(client)

    listing = client.get("/api/shortlist", headers=shopper)

    assert listing.status_code == 200
    assert listing.json()["items"] == []
    assert listing.json()["project_ids"] == []