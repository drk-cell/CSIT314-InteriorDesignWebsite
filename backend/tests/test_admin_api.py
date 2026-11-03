"""Administrators approve and suspend accounts."""

from __future__ import annotations

from typing import Any

from fastapi.testclient import TestClient

from app.domain.enums import Role
from app.services.account_service import AccountService

ADMIN = {"email": "admin@example.com", "password": "passw0rd123"}

CUSTOMER: dict[str, Any] = {
    "email": "casey@example.com",
    "password": "design4me",
    "display_name": "Casey",
    "role": "CUSTOMER",
}

DESIGNER: dict[str, Any] = {
    "email": "dana@example.com",
    "password": "design4me",
    "display_name": "Dana Studio",
    "role": "DESIGNER",
}


def create_admin(account_service: AccountService) -> None:
    """Put one active administrator in the shared store."""
    account_service.ensure_staff_account(
        ADMIN["email"], ADMIN["password"], "Administrator", Role.ADMIN
    )


def token_for(client: TestClient, email: str, password: str) -> str:
    """Sign in and return the bearer token."""
    response = client.post("/api/auth/login", json={"email": email, "password": password})
    assert response.status_code == 200, response.text
    return response.json()["access_token"]


def auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def test_list_accounts_requires_a_token(client: TestClient) -> None:
    response = client.get("/api/admin/accounts")
    assert response.status_code == 401


def test_list_accounts_rejects_a_customer(
    client: TestClient, account_service: AccountService
) -> None:
    create_admin(account_service)
    client.post("/api/auth/register", json=CUSTOMER)
    token = token_for(client, CUSTOMER["email"], CUSTOMER["password"])

    response = client.get("/api/admin/accounts", headers=auth(token))

    assert response.status_code == 403


def test_admin_lists_pending_designers(
    client: TestClient, account_service: AccountService
) -> None:
    create_admin(account_service)
    client.post("/api/auth/register", json=DESIGNER)
    client.post("/api/auth/register", json=CUSTOMER)
    token = token_for(client, ADMIN["email"], ADMIN["password"])

    response = client.get("/api/admin/accounts?status=PENDING", headers=auth(token))

    assert response.status_code == 200
    body = response.json()
    assert [account["email"] for account in body] == [DESIGNER["email"]]
    assert body[0]["status"] == "PENDING"


def test_approve_lets_the_designer_sign_in(
    client: TestClient, account_service: AccountService
) -> None:
    create_admin(account_service)
    created = client.post("/api/auth/register", json=DESIGNER).json()
    token = token_for(client, ADMIN["email"], ADMIN["password"])

    response = client.post(
        f"/api/admin/accounts/{created['id']}/approve", headers=auth(token)
    )

    assert response.status_code == 200
    assert response.json()["status"] == "ACTIVE"
    signed_in = client.post(
        "/api/auth/login",
        json={"email": DESIGNER["email"], "password": DESIGNER["password"]},
    )
    assert signed_in.status_code == 200


def test_suspend_blocks_the_next_sign_in(
    client: TestClient, account_service: AccountService
) -> None:
    create_admin(account_service)
    created = client.post("/api/auth/register", json=CUSTOMER).json()
    token = token_for(client, ADMIN["email"], ADMIN["password"])

    response = client.post(
        f"/api/admin/accounts/{created['id']}/suspend", headers=auth(token)
    )

    assert response.status_code == 200
    assert response.json()["status"] == "SUSPENDED"
    blocked = client.post(
        "/api/auth/login",
        json={"email": CUSTOMER["email"], "password": CUSTOMER["password"]},
    )
    assert blocked.status_code == 403
    assert blocked.json()["detail"] == "Account suspended"


def test_admin_cannot_change_their_own_status(
    client: TestClient, account_service: AccountService
) -> None:
    create_admin(account_service)
    token = token_for(client, ADMIN["email"], ADMIN["password"])
    accounts = client.get("/api/admin/accounts", headers=auth(token)).json()
    own_id = next(account["id"] for account in accounts if account["email"] == ADMIN["email"])

    response = client.post(
        f"/api/admin/accounts/{own_id}/suspend", headers=auth(token)
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "You cannot change your own account status"


def test_unknown_account_returns_404(
    client: TestClient, account_service: AccountService
) -> None:
    create_admin(account_service)
    token = token_for(client, ADMIN["email"], ADMIN["password"])

    response = client.post(
        "/api/admin/accounts/does-not-exist/approve", headers=auth(token)
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Account not found"


def test_status_filter_is_validated(
    client: TestClient, account_service: AccountService
) -> None:
    create_admin(account_service)
    token = token_for(client, ADMIN["email"], ADMIN["password"])

    response = client.get("/api/admin/accounts?status=NONSENSE", headers=auth(token))

    assert response.status_code == 422