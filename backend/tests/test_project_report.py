"""Project reports: a customer reports, staff act, the project leaves the catalogue."""

from __future__ import annotations

from typing import Any

from fastapi.testclient import TestClient

from app.api.deps import get_account_repository, get_account_service
from app.domain.enums import AccountStatus, Role

PROJECT: dict[str, Any] = {
    "title": "Warm Minimal Living Room",
    "description": "A compact flat opened up.",
    "style": "Minimal",
    "category": "Living Room",
    "budget_min": 20000,
    "budget_max": 40000,
    "images": ["/portfolio/photos/photo-01.jpg"],
}

ADMIN = {"email": "admin@example.com", "password": "passw0rd123"}


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


def designer(client: TestClient, email: str = "dana@example.com") -> dict[str, str]:
    """A signed in designer with a company."""
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
            "name": f"Studio {email}",
            "contact_email": email,
            "meeting_address": "12 Orchard Road, Singapore",
        },
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


def admin(client: TestClient) -> dict[str, str]:
    """One active administrator, signed in."""
    get_account_service().ensure_staff_account(
        ADMIN["email"], ADMIN["password"], "Administrator", Role.ADMIN
    )
    response = client.post("/api/auth/login", json=ADMIN)
    assert response.status_code == 200, response.text
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def publish(client: TestClient, headers: dict[str, str]) -> str:
    """Create one project and return its id."""
    response = client.post("/api/projects", json=PROJECT, headers=headers)
    assert response.status_code == 201, response.text
    return response.json()["id"]


def report(
    client: TestClient,
    headers: dict[str, str],
    project_id: str,
    *,
    reason: str = "Inappropriate content",
    comments: str = "The photos do not belong to this studio.",
):
    """Post one report and return the response."""
    return client.post(
        "/api/project-reports",
        json={"project_id": project_id, "reason": reason, "comments": comments},
        headers=headers,
    )


# --- reporting ------------------------------------------------------------


def test_a_customer_reports_a_project(client: TestClient) -> None:
    owner = designer(client)
    casey = customer(client)
    project_id = publish(client, owner)
    response = report(client, casey, project_id)
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["status"] == "OPEN"
    assert body["reason"] == "Inappropriate content"
    assert body["project_title"] == "Warm Minimal Living Room"
    assert body["designer_name"] == "Dana Studio"
    assert body["customer_name"] == "Casey"


def test_a_reason_outside_the_list_is_refused(client: TestClient) -> None:
    owner = designer(client)
    casey = customer(client)
    project_id = publish(client, owner)
    response = report(client, casey, project_id, reason="I do not like it")
    assert response.status_code == 400


def test_a_report_needs_a_real_project(client: TestClient) -> None:
    casey = customer(client)
    response = report(client, casey, "no-such-project")
    assert response.status_code == 404


def test_a_designer_cannot_report(client: TestClient) -> None:
    owner = designer(client)
    project_id = publish(client, owner)
    response = report(client, owner, project_id)
    assert response.status_code == 403


def test_an_admin_cannot_report(client: TestClient) -> None:
    owner = designer(client)
    admin_headers = admin(client)
    project_id = publish(client, owner)
    response = report(client, admin_headers, project_id)
    assert response.status_code == 403


def test_one_open_report_per_customer_and_project(client: TestClient) -> None:
    owner = designer(client)
    casey = customer(client)
    project_id = publish(client, owner)
    assert report(client, casey, project_id).status_code == 201
    assert report(client, casey, project_id).status_code == 409


# --- the staff list -------------------------------------------------------


def test_staff_read_the_report_queue(client: TestClient) -> None:
    owner = designer(client)
    casey = customer(client)
    admin_headers = admin(client)
    report(client, casey, publish(client, owner))
    response = client.get("/api/project-reports", headers=admin_headers)
    assert response.status_code == 200, response.text
    rows = response.json()
    assert len(rows) == 1
    assert rows[0]["project_title"] == "Warm Minimal Living Room"
    assert rows[0]["designer_email"] == "dana@example.com"
    assert rows[0]["customer_name"] == "Casey"


def test_a_customer_cannot_read_the_queue(client: TestClient) -> None:
    owner = designer(client)
    casey = customer(client)
    project_id = publish(client, owner)
    report(client, casey, project_id)
    assert client.get("/api/project-reports", headers=casey).status_code == 403


# --- resolution -----------------------------------------------------------


def resolve(client: TestClient, headers: dict[str, str], report_id: str, **body: Any):
    """Close one report with the chosen actions."""
    return client.post(
        f"/api/project-reports/{report_id}/resolve", json=body, headers=headers
    )


def test_taking_a_project_down_hides_it(client: TestClient) -> None:
    owner = designer(client)
    casey = customer(client)
    admin_headers = admin(client)
    project_id = publish(client, owner)
    created = report(client, casey, project_id).json()

    response = resolve(client, admin_headers, created["id"], take_down=True)
    assert response.status_code == 200, response.text
    assert response.json()["status"] == "ACTIONED"

    assert client.get(f"/api/projects/{project_id}", headers=casey).status_code == 404
    assert client.get(f"/api/projects/{project_id}", headers=owner).status_code == 200
    search = client.get("/api/projects/search", headers=casey).json()
    assert search["total"] == 0


def test_taking_a_project_down_removes_it_from_a_shortlist(
    client: TestClient,
) -> None:
    owner = designer(client)
    casey = customer(client)
    admin_headers = admin(client)
    project_id = publish(client, owner)
    assert (
        client.post(f"/api/shortlist/{project_id}", headers=casey).status_code == 201
    )
    created = report(client, casey, project_id).json()
    resolve(client, admin_headers, created["id"], take_down=True)
    saved = client.get("/api/shortlist", headers=casey).json()
    assert saved["items"] == []


def test_suspending_the_designer_blocks_their_login(client: TestClient) -> None:
    owner = designer(client)
    casey = customer(client)
    admin_headers = admin(client)
    project_id = publish(client, owner)
    created = report(client, casey, project_id).json()

    response = resolve(client, admin_headers, created["id"], suspend_designer=True)
    assert response.status_code == 200, response.text
    assert response.json()["status"] == "ACTIONED"
    stored = get_account_repository().get_by_email("dana@example.com")
    assert stored is not None
    assert stored.status is AccountStatus.SUSPENDED
    login = client.post(
        "/api/auth/login",
        json={"email": "dana@example.com", "password": "design4me"},
    )
    assert login.status_code == 403


def test_both_actions_apply_to_one_report(client: TestClient) -> None:
    owner = designer(client)
    casey = customer(client)
    admin_headers = admin(client)
    project_id = publish(client, owner)
    created = report(client, casey, project_id).json()

    response = resolve(
        client,
        admin_headers,
        created["id"],
        take_down=True,
        suspend_designer=True,
    )
    assert response.status_code == 200, response.text
    assert client.get(f"/api/projects/{project_id}", headers=casey).status_code == 404
    stored = get_account_repository().get_by_email("dana@example.com")
    assert stored is not None and stored.status is AccountStatus.SUSPENDED


def test_no_action_dismisses_the_report(client: TestClient) -> None:
    owner = designer(client)
    casey = customer(client)
    admin_headers = admin(client)
    project_id = publish(client, owner)
    created = report(client, casey, project_id).json()

    response = resolve(client, admin_headers, created["id"])
    assert response.status_code == 200, response.text
    assert response.json()["status"] == "DISMISSED"
    assert client.get(f"/api/projects/{project_id}", headers=casey).status_code == 200


def test_a_closed_report_cannot_be_resolved_twice(client: TestClient) -> None:
    owner = designer(client)
    casey = customer(client)
    admin_headers = admin(client)
    created = report(client, casey, publish(client, owner)).json()
    assert resolve(client, admin_headers, created["id"], take_down=True).status_code == 200
    again = resolve(client, admin_headers, created["id"], take_down=True)
    assert again.status_code == 409


def test_a_customer_cannot_resolve_a_report(client: TestClient) -> None:
    owner = designer(client)
    casey = customer(client)
    created = report(client, casey, publish(client, owner)).json()
    response = resolve(client, casey, created["id"], take_down=True)
    assert response.status_code == 403


def test_a_designer_cannot_take_their_own_project_down(client: TestClient) -> None:
    owner = designer(client)
    project_id = publish(client, owner)
    response = client.patch(
        f"/api/projects/{project_id}", json={"status": "TAKEN_DOWN"}, headers=owner
    )
    assert response.status_code == 403
