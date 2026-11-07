"""Quoting: money, entities, states and the endpoints."""

from __future__ import annotations

from datetime import date, timedelta
from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.api.deps import get_account_repository
from app.domain.enums import QuoteRequestState, QuoteState
from app.domain.errors import InvalidState
from app.domain.money import format_cents, gst_component, grand_total
from app.domain.quote import Quote
from app.domain.quote_request import MAX_COUNTERS, QuoteRequest

# --- money ----------------------------------------------------------------


def test_gst_is_added_when_the_total_excludes_it() -> None:
    assert gst_component(10_000) == 900
    assert grand_total(10_000) == 10_900


def test_gst_is_extracted_when_the_total_includes_it() -> None:
    assert gst_component(10_900, included=True) == 900
    assert grand_total(10_900, included=True) == 10_900


def test_money_formats_to_dollars_and_cents() -> None:
    assert format_cents(123_456) == "S$1,234.56"
    assert format_cents(0) == "S$0.00"


# --- entities -------------------------------------------------------------


def make_quote(**overrides: Any) -> Quote:
    values: dict[str, Any] = {
        "request_id": "request-1",
        "total_cents": 10_000,
        "valid_until": date.today() + timedelta(days=14),
    }
    values.update(overrides)
    return Quote(**values)


def test_a_quote_needs_a_positive_total() -> None:
    with pytest.raises(ValueError):
        make_quote(total_cents=0)


def test_a_quote_needs_a_sane_validity_window() -> None:
    with pytest.raises(ValueError):
        make_quote(valid_until=date.today())
    with pytest.raises(ValueError):
        make_quote(valid_until=date.today() + timedelta(days=91))


def test_an_expired_quote_cannot_be_accepted() -> None:
    quote = make_quote(valid_until=date.today() + timedelta(days=1))
    quote.valid_until = date.today() - timedelta(days=1)

    with pytest.raises(ValueError):
        quote.accept()


def test_a_request_refuses_a_budget_floor_above_the_ceiling() -> None:
    with pytest.raises(ValueError):
        QuoteRequest(
            customer_id="casey",
            company_id="company-1",
            title="Kitchen",
            scope="Full renovation",
            budget_min_cents=50_000,
            budget_max_cents=10_000,
        )


def test_the_counter_list_is_bounded() -> None:
    request = QuoteRequest(
        customer_id="casey",
        company_id="company-1",
        title="Kitchen",
        scope="Full renovation",
    )
    for index in range(MAX_COUNTERS):
        request.counter(10_000 + index, "target")

    with pytest.raises(ValueError):
        request.counter(20_000, "one more")


def test_a_closed_request_takes_no_counter() -> None:
    request = QuoteRequest(
        customer_id="casey",
        company_id="company-1",
        title="Kitchen",
        scope="Full renovation",
    )
    request.cancel("changed my mind")

    with pytest.raises(ValueError):
        request.counter(10_000, "target")


def test_only_the_pending_request_can_be_refused() -> None:
    request = QuoteRequest(
        customer_id="casey",
        company_id="company-1",
        title="Kitchen",
        scope="Full renovation",
    )
    request.mark_answered()

    with pytest.raises(ValueError):
        request.refuse("busy")


# --- endpoints ------------------------------------------------------------


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
    response = client.post(
        "/api/companies",
        json={"name": f"Studio {email}", "contact_email": email},
        headers=headers,
    )
    assert response.status_code == 201, response.text
    headers["company_id"] = response.json()["id"]
    return headers


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


def submit(
    client: TestClient, shopper: dict[str, str], company_id: str, title: str = "Kitchen"
) -> dict[str, Any]:
    response = client.post(
        "/api/quotes/requests",
        json={
            "company_id": company_id,
            "title": title,
            "scope": "Full kitchen renovation, 4 room flat.",
            "budget_min_cents": 2_000_000,
            "budget_max_cents": 4_000_000,
            "target_cents": 3_000_000,
        },
        headers=shopper,
    )
    assert response.status_code == 201, response.text
    return response.json()


def test_a_customer_submits_a_request(client: TestClient) -> None:
    owner = designer(client)
    shopper = customer(client)

    body = submit(client, shopper, owner["company_id"])

    assert body["state"] == QuoteRequestState.PENDING.value
    assert body["target_cents"] == 3_000_000
    assert body["customer_id"]


def test_a_designer_cannot_submit(client: TestClient) -> None:
    owner = designer(client)

    response = client.post(
        "/api/quotes/requests",
        json={
            "company_id": owner["company_id"],
            "title": "Kitchen",
            "scope": "Full renovation",
        },
        headers=owner,
    )

    assert response.status_code == 403


def test_one_open_request_per_company(client: TestClient) -> None:
    owner = designer(client)
    shopper = customer(client)
    submit(client, shopper, owner["company_id"])

    second = client.post(
        "/api/quotes/requests",
        json={
            "company_id": owner["company_id"],
            "title": "Kitchen again",
            "scope": "Same flat",
        },
        headers=shopper,
    )

    assert second.status_code == 409


def test_the_designer_answers_with_a_total(client: TestClient) -> None:
    owner = designer(client)
    shopper = customer(client)
    request = submit(client, shopper, owner["company_id"])

    response = client.post(
        f"/api/quotes/requests/{request['id']}/quotes",
        json={"total_cents": 3_500_000, "valid_days": 14, "gst_included": False},
        headers=owner,
    )

    assert response.status_code == 201, response.text
    body = response.json()
    assert body["version"] == 1
    assert body["gst_cents"] == 315_000
    assert body["grand_total_cents"] == 3_815_000
    assert body["state"] == QuoteState.OFFERED.value


def test_the_customer_names_a_target_price(client: TestClient) -> None:
    owner = designer(client)
    shopper = customer(client)
    request = submit(client, shopper, owner["company_id"])
    client.post(
        f"/api/quotes/requests/{request['id']}/quotes",
        json={"total_cents": 3_500_000, "valid_days": 14, "gst_included": False},
        headers=owner,
    )

    response = client.post(
        f"/api/quotes/requests/{request['id']}/counter",
        json={"target_cents": 3_200_000, "note": "Can you meet this?"},
        headers=shopper,
    )

    assert response.status_code == 200
    assert response.json()["counters"][0]["target_cents"] == 3_200_000


def test_a_revision_supersedes_the_old_version(client: TestClient) -> None:
    owner = designer(client)
    shopper = customer(client)
    request = submit(client, shopper, owner["company_id"])
    first = client.post(
        f"/api/quotes/requests/{request['id']}/quotes",
        json={"total_cents": 3_500_000, "valid_days": 14, "gst_included": False},
        headers=owner,
    ).json()

    second = client.post(
        f"/api/quotes/{first['id']}/revise",
        json={"total_cents": 3_200_000, "valid_days": 14, "gst_included": False},
        headers=owner,
    )
    versions = client.get(
        f"/api/quotes/requests/{request['id']}/quotes", headers=shopper
    ).json()

    assert second.status_code == 201
    assert second.json()["version"] == 2
    assert [entry["state"] for entry in versions] == [
        QuoteState.SUPERSEDED.value,
        QuoteState.OFFERED.value,
    ]


def test_a_fourth_version_is_refused(client: TestClient) -> None:
    owner = designer(client)
    shopper = customer(client)
    request = submit(client, shopper, owner["company_id"])
    quote = client.post(
        f"/api/quotes/requests/{request['id']}/quotes",
        json={"total_cents": 3_500_000, "valid_days": 14},
        headers=owner,
    ).json()
    for _ in range(2):
        quote = client.post(
            f"/api/quotes/{quote['id']}/revise",
            json={"total_cents": 3_400_000, "valid_days": 14},
            headers=owner,
        ).json()

    fourth = client.post(
        f"/api/quotes/{quote['id']}/revise",
        json={"total_cents": 3_300_000, "valid_days": 14},
        headers=owner,
    )

    assert fourth.status_code == 409


def test_accepting_closes_only_that_request(client: TestClient) -> None:
    first_owner = designer(client, "dana@example.com")
    second_owner = designer(client, "other@example.com")
    shopper = customer(client)
    first = submit(client, shopper, first_owner["company_id"], "Kitchen")
    second = submit(client, shopper, second_owner["company_id"], "Bedroom")
    quote = client.post(
        f"/api/quotes/requests/{first['id']}/quotes",
        json={"total_cents": 3_500_000, "valid_days": 14},
        headers=first_owner,
    ).json()

    accepted = client.post(f"/api/quotes/{quote['id']}/accept", headers=shopper)
    other = client.get(f"/api/quotes/requests/{second['id']}", headers=shopper)

    assert accepted.status_code == 200
    assert accepted.json()["state"] == QuoteState.ACCEPTED.value
    assert other.json()["state"] == QuoteRequestState.PENDING.value


def test_the_company_sees_the_request_in_its_inbox(client: TestClient) -> None:
    owner = designer(client)
    shopper = customer(client)
    submit(client, shopper, owner["company_id"])

    inbox = client.get("/api/quotes/requests", headers=owner)

    assert inbox.status_code == 200
    assert len(inbox.json()) == 1


def test_another_customer_cannot_read_the_request(client: TestClient) -> None:
    owner = designer(client)
    shopper = customer(client)
    request = submit(client, shopper, owner["company_id"])
    stranger = customer(client, "other-customer@example.com")

    response = client.get(f"/api/quotes/requests/{request['id']}", headers=stranger)

    assert response.status_code == 403


def test_the_customer_cancels_the_request(client: TestClient) -> None:
    owner = designer(client)
    shopper = customer(client)
    request = submit(client, shopper, owner["company_id"])

    response = client.post(
        f"/api/quotes/requests/{request['id']}/cancel",
        json={"reason": "Found another designer"},
        headers=shopper,
    )

    assert response.status_code == 200
    assert response.json()["state"] == QuoteRequestState.CANCELLED.value


def test_a_cancelled_request_cannot_be_answered(client: TestClient) -> None:
    owner = designer(client)
    shopper = customer(client)
    request = submit(client, shopper, owner["company_id"])
    client.post(
        f"/api/quotes/requests/{request['id']}/cancel", json={}, headers=shopper
    )

    response = client.post(
        f"/api/quotes/requests/{request['id']}/quotes",
        json={"total_cents": 3_500_000, "valid_days": 14},
        headers=owner,
    )

    assert response.status_code == 409


def test_the_designer_declines_the_request(client: TestClient) -> None:
    owner = designer(client)
    shopper = customer(client)
    request = submit(client, shopper, owner["company_id"])

    response = client.post(
        f"/api/quotes/requests/{request['id']}/refuse",
        json={"reason": "Fully booked until March"},
        headers=owner,
    )

    assert response.status_code == 200
    assert response.json()["state"] == QuoteRequestState.REFUSED.value


def test_a_customer_cannot_answer_their_own_request(client: TestClient) -> None:
    owner = designer(client)
    shopper = customer(client)
    request = submit(client, shopper, owner["company_id"])

    response = client.post(
        f"/api/quotes/requests/{request['id']}/quotes",
        json={"total_cents": 1_000, "valid_days": 7},
        headers=shopper,
    )

    assert response.status_code == 403