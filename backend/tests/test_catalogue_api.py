"""The catalogue endpoint publishes the fixed vocabulary."""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.domain import catalogue


def test_the_catalogue_is_public(client: TestClient) -> None:
    response = client.get("/api/catalogue")

    assert response.status_code == 200


def test_it_returns_every_category_and_style(client: TestClient) -> None:
    body = client.get("/api/catalogue").json()

    assert body["categories"] == list(catalogue.CATEGORIES)
    assert body["styles"] == list(catalogue.STYLES)
    assert len(body["categories"]) == 10
    assert len(body["styles"]) == 7


def test_it_returns_the_budget_bounds(client: TestClient) -> None:
    body = client.get("/api/catalogue").json()

    assert body["budget"] == {"min": 0, "max": 200000, "step": 5000}


def test_the_lists_have_no_duplicates(client: TestClient) -> None:
    body = client.get("/api/catalogue").json()

    assert len(set(body["categories"])) == len(body["categories"])
    assert len(set(body["styles"])) == len(body["styles"])