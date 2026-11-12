"""Consultation booking: the slot grid, the state machine and the endpoints."""

from __future__ import annotations

from datetime import date, timedelta
from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.api.deps import get_account_repository
from app.domain.appointment import (
    BOOKING_DAYS,
    SLOT_TIMES,
    ConsultationAppointment,
    is_bookable_date,
)

# --- helpers --------------------------------------------------------------


def sign_in(client: TestClient, account: dict[str, Any]) -> dict[str, str]:
    """Register, activate and sign in, returning the auth header."""
    registered = client.post("/api/auth/register", json=account)
    assert registered.status_code == 201, registered.text
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
        json={"name": f"Studio {email}", "contact_email": email},
        headers=headers,
    )
    assert response.status_code == 201, response.text
    headers["company_id"] = response.json()["id"]
    return headers


def customer(client: TestClient, email: str = "casey@example.com") -> dict[str, str]:
    """A signed in customer."""
    return sign_in(
        client,
        {
            "email": email,
            "password": "casey4me",
            "display_name": "Casey",
            "role": "CUSTOMER",
        },
    )


def tomorrow(days: int = 1) -> str:
    """Return a bookable day as an ISO string."""
    return (date.today() + timedelta(days=days)).isoformat()


def book(
    client: TestClient,
    headers: dict[str, str],
    company_id: str,
    *,
    when: str | None = None,
    time: str = "10:00",
    requirements: str = "Two bedrooms, warm light.",
):
    """Post one booking and return the response."""
    return client.post(
        "/api/appointments",
        json={
            "company_id": company_id,
            "date": when or tomorrow(),
            "time": time,
            "requirements": requirements,
        },
        headers=headers,
    )


# --- the slot grid --------------------------------------------------------


def test_the_working_day_holds_nine_hours() -> None:
    assert len(SLOT_TIMES) == 9
    assert SLOT_TIMES[0] == "09:00"
    assert SLOT_TIMES[-1] == "17:00"


def test_the_window_starts_today_and_stops_after_two_weeks() -> None:
    today = date.today()
    assert is_bookable_date(today)
    assert is_bookable_date(today + timedelta(days=BOOKING_DAYS - 1))
    assert not is_bookable_date(today - timedelta(days=1))
    assert not is_bookable_date(today + timedelta(days=BOOKING_DAYS))


def test_an_appointment_refuses_a_bad_slot() -> None:
    with pytest.raises(ValueError):
        ConsultationAppointment(
            customer_id="c1",
            company_id="k1",
            appointment_date=date.today() + timedelta(days=1),
            appointment_time="08:00",
        )


def test_an_appointment_accepts_once_and_cancels_once() -> None:
    appointment = ConsultationAppointment(
        customer_id="c1",
        company_id="k1",
        appointment_date=date.today() + timedelta(days=1),
        appointment_time="10:00",
    )
    assert appointment.is_pending()
    appointment.accept()
    assert appointment.state.value == "ACCEPTED"
    with pytest.raises(ValueError):
        appointment.accept()
    appointment.cancel()
    assert appointment.state.value == "CANCELLED"
    with pytest.raises(ValueError):
        appointment.cancel()


# --- the boundary ---------------------------------------------------------


def test_slots_list_every_free_hour(client: TestClient) -> None:
    owner = designer(client)
    response = client.get(
        "/api/appointments/slots",
        params={"company_id": owner["company_id"], "date": tomorrow()},
        headers=owner,
    )
    assert response.status_code == 200, response.text
    assert response.json()["slots"] == list(SLOT_TIMES)


def test_a_day_outside_the_window_is_refused(client: TestClient) -> None:
    owner = designer(client)
    response = client.get(
        "/api/appointments/slots",
        params={"company_id": owner["company_id"], "date": tomorrow(30)},
        headers=owner,
    )
    assert response.status_code == 400


def test_slots_need_a_signed_in_account(client: TestClient) -> None:
    owner = designer(client)
    response = client.get(
        "/api/appointments/slots",
        params={"company_id": owner["company_id"], "date": tomorrow()},
    )
    assert response.status_code == 401


def test_a_customer_books_a_pending_appointment(client: TestClient) -> None:
    owner = designer(client)
    casey = customer(client)
    response = book(client, casey, owner["company_id"])
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["state"] == "PENDING"
    assert body["appointment_date"] == tomorrow()
    assert body["appointment_time"] == "10:00"
    assert body["notified_at"] is not None
    assert body["customer_name"] == "Casey"


def test_the_same_slot_cannot_be_booked_twice(client: TestClient) -> None:
    owner = designer(client)
    casey = customer(client)
    other = customer(client, "robin@example.com")
    assert book(client, casey, owner["company_id"]).status_code == 201
    response = book(client, other, owner["company_id"])
    assert response.status_code == 409
    slots = client.get(
        "/api/appointments/slots",
        params={"company_id": owner["company_id"], "date": tomorrow()},
        headers=other,
    ).json()["slots"]
    assert "10:00" not in slots


def test_a_customer_holds_one_open_appointment_per_company(
    client: TestClient,
) -> None:
    owner = designer(client)
    casey = customer(client)
    assert book(client, casey, owner["company_id"]).status_code == 201
    response = book(client, casey, owner["company_id"], time="14:00")
    assert response.status_code == 409


def test_the_designer_reads_the_booking_with_the_customer_name(
    client: TestClient,
) -> None:
    owner = designer(client)
    casey = customer(client)
    book(client, casey, owner["company_id"])
    response = client.get("/api/appointments", headers=owner)
    assert response.status_code == 200, response.text
    rows = response.json()
    assert len(rows) == 1
    assert rows[0]["customer_name"] == "Casey"
    assert rows[0]["requirements"] == "Two bedrooms, warm light."


def test_a_designer_accepts_a_pending_booking(client: TestClient) -> None:
    owner = designer(client)
    casey = customer(client)
    created = book(client, casey, owner["company_id"]).json()
    response = client.post(
        f"/api/appointments/{created['id']}/accept", headers=owner
    )
    assert response.status_code == 200, response.text
    assert response.json()["state"] == "ACCEPTED"
    again = client.post(f"/api/appointments/{created['id']}/accept", headers=owner)
    assert again.status_code == 409


def test_only_the_owner_designer_accepts(client: TestClient) -> None:
    owner = designer(client)
    other = designer(client, "rival@example.com")
    casey = customer(client)
    created = book(client, casey, owner["company_id"]).json()
    response = client.post(
        f"/api/appointments/{created['id']}/accept", headers=other
    )
    assert response.status_code == 403


def test_a_customer_cannot_accept(client: TestClient) -> None:
    owner = designer(client)
    casey = customer(client)
    created = book(client, casey, owner["company_id"]).json()
    response = client.post(
        f"/api/appointments/{created['id']}/accept", headers=casey
    )
    assert response.status_code == 403


def test_a_customer_cancels_and_the_slot_returns(client: TestClient) -> None:
    owner = designer(client)
    casey = customer(client)
    created = book(client, casey, owner["company_id"]).json()
    response = client.post(
        f"/api/appointments/{created['id']}/cancel", headers=casey
    )
    assert response.status_code == 200, response.text
    assert response.json()["state"] == "CANCELLED"
    slots = client.get(
        "/api/appointments/slots",
        params={"company_id": owner["company_id"], "date": tomorrow()},
        headers=casey,
    ).json()["slots"]
    assert "10:00" in slots


def test_cancelling_twice_is_refused(client: TestClient) -> None:
    owner = designer(client)
    casey = customer(client)
    created = book(client, casey, owner["company_id"]).json()
    assert (
        client.post(
            f"/api/appointments/{created['id']}/cancel", headers=casey
        ).status_code
        == 200
    )
    again = client.post(f"/api/appointments/{created['id']}/cancel", headers=casey)
    assert again.status_code == 409


def test_a_designer_cancels_a_booking(client: TestClient) -> None:
    owner = designer(client)
    casey = customer(client)
    created = book(client, casey, owner["company_id"]).json()
    response = client.post(
        f"/api/appointments/{created['id']}/cancel", headers=owner
    )
    assert response.status_code == 200, response.text
    assert response.json()["state"] == "CANCELLED"


def test_another_customer_cannot_cancel(client: TestClient) -> None:
    owner = designer(client)
    casey = customer(client)
    other = customer(client, "robin@example.com")
    created = book(client, casey, owner["company_id"]).json()
    response = client.post(
        f"/api/appointments/{created['id']}/cancel", headers=other
    )
    assert response.status_code == 403


def test_a_designer_cannot_book(client: TestClient) -> None:
    owner = designer(client)
    response = book(client, owner, owner["company_id"])
    assert response.status_code == 403


def test_an_unknown_company_is_refused(client: TestClient) -> None:
    casey = customer(client)
    response = book(client, casey, "no-such-company")
    assert response.status_code == 404


def test_a_time_outside_the_grid_is_refused(client: TestClient) -> None:
    owner = designer(client)
    casey = customer(client)
    assert book(client, casey, owner["company_id"], time="08:00").status_code == 400
    assert book(client, casey, owner["company_id"], time="12:30").status_code == 400


def test_a_past_day_is_refused(client: TestClient) -> None:
    owner = designer(client)
    casey = customer(client)
    yesterday = (date.today() - timedelta(days=1)).isoformat()
    response = book(client, casey, owner["company_id"], when=yesterday)
    assert response.status_code == 400


def test_a_customer_reads_only_their_own_bookings(client: TestClient) -> None:
    owner = designer(client)
    casey = customer(client)
    robin = customer(client, "robin@example.com")
    book(client, casey, owner["company_id"])
    rows = client.get("/api/appointments", headers=robin).json()
    assert rows == []
