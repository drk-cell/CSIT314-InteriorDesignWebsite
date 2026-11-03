"""The auth endpoints honour the published request and response contract."""

from __future__ import annotations

from typing import Any

from fastapi.testclient import TestClient

from app.repositories.account_repository import AccountRepository

CUSTOMER: dict[str, Any] = {
    "email": "Casey@Example.com",
    "password": "design4me",
    "display_name": "Casey",
    "role": "CUSTOMER",
}


def register(client: TestClient, **overrides: Any) -> Any:
    payload = {**CUSTOMER, **overrides}
    return client.post("/api/auth/register", json=payload)


def login(client: TestClient, **overrides: Any) -> Any:
    payload = {"email": CUSTOMER["email"], "password": CUSTOMER["password"], **overrides}
    return client.post("/api/auth/login", json=payload)


def test_register_returns_201_and_lowercases_email(client: TestClient) -> None:
    response = register(client)
    assert response.status_code == 201
    body = response.json()
    assert body["email"] == "casey@example.com"
    assert body["status"] == "ACTIVE"
    assert body["role"] == "CUSTOMER"
    assert body["display_name"] == "Casey"
    assert set(body) == {"id", "email", "display_name", "role", "status", "created_at"}


def test_register_designer_starts_pending(client: TestClient) -> None:
    response = register(client, email="dana@example.com", role="DESIGNER")
    assert response.status_code == 201
    assert response.json()["status"] == "PENDING"


def test_register_duplicate_email_returns_409(client: TestClient) -> None:
    register(client)
    response = register(client, email="CASEY@example.com")
    assert response.status_code == 409
    assert response.json()["detail"] == "Email is already registered"


def test_register_admin_role_returns_400(client: TestClient) -> None:
    response = register(client, email="root@example.com", role="ADMIN")
    assert response.status_code == 400
    assert "detail" in response.json()


def test_register_platform_manager_role_returns_400(client: TestClient) -> None:
    response = register(client, email="boss@example.com", role="PLATFORM_MANAGER")
    assert response.status_code == 400


def test_register_short_password_returns_400(client: TestClient) -> None:
    response = register(client, password="short")
    assert response.status_code == 400
    assert "8" in response.json()["detail"]


def test_login_returns_a_token(client: TestClient) -> None:
    register(client)
    response = login(client)
    assert response.status_code == 200
    body = response.json()
    assert body["token_type"] == "bearer"
    assert body["expires_in"] > 0
    assert isinstance(body["access_token"], str) and body["access_token"]
    assert body["account"]["email"] == "casey@example.com"
    assert set(body) == {"access_token", "token_type", "expires_in", "account"}


def test_login_wrong_password_returns_401(client: TestClient) -> None:
    register(client)
    response = login(client, password="wrong-password")
    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid email or password"


def test_login_pending_designer_returns_403(client: TestClient) -> None:
    register(client, email="dana@example.com", role="DESIGNER")
    response = login(client, email="dana@example.com")
    assert response.status_code == 403
    assert response.json()["detail"] == "Account pending approval"


def test_me_without_token_returns_401(client: TestClient) -> None:
    response = client.get("/api/auth/me")
    assert response.status_code == 401
    assert "detail" in response.json()


def test_me_with_token_returns_the_account(client: TestClient) -> None:
    created = register(client).json()
    token = login(client).json()["access_token"]
    response = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    assert response.json()["id"] == created["id"]
    assert response.json()["email"] == "casey@example.com"


def test_me_with_garbage_token_returns_401(client: TestClient) -> None:
    response = client.get("/api/auth/me", headers={"Authorization": "Bearer not-a-token"})
    assert response.status_code == 401
    assert "detail" in response.json()


def test_me_with_wrong_scheme_returns_401(client: TestClient) -> None:
    register(client)
    token = login(client).json()["access_token"]
    response = client.get("/api/auth/me", headers={"Authorization": f"Basic {token}"})
    assert response.status_code == 401


def test_me_after_suspension_returns_403(
    client: TestClient, account_repository: AccountRepository
) -> None:
    register(client)
    token = login(client).json()["access_token"]
    account = account_repository.get_by_email("casey@example.com")
    assert account is not None
    account.suspend()

    response = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 403
    assert response.json()["detail"] == "Account suspended"