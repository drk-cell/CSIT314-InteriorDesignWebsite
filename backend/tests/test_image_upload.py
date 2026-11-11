"""The endpoint that keeps a designer's photo.

The tag reader drops the file after reading it. A project needs the picture
itself, so this endpoint writes it to disk and answers with the address the
browser will ask for. These tests cover the refusals, because they are the only
part a user can trip over.
"""

from __future__ import annotations

from io import BytesIO
from typing import Any

from fastapi.testclient import TestClient
from PIL import Image

from app.api.deps import get_account_repository


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


def designer(client: TestClient, email: str) -> dict[str, str]:
    return sign_in(
        client,
        {
            "email": email,
            "password": "design4me",
            "display_name": "Studio",
            "role": "DESIGNER",
        },
    )


def photo_bytes(colour: tuple[int, int, int] = (120, 140, 160)) -> bytes:
    buffer = BytesIO()
    Image.new("RGB", (96, 64), colour).save(buffer, format="JPEG")
    return buffer.getvalue()


def test_a_photo_is_kept_and_addressed(client: TestClient, tmp_path) -> None:
    headers = designer(client, "keeper@example.com")

    response = client.post(
        "/api/images",
        headers=headers,
        files={"file": ("room.jpg", photo_bytes(), "image/jpeg")},
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["url"].startswith("/uploads/")
    assert body["url"].endswith(".jpg")
    assert (body["width"], body["height"]) == (96, 64)

    # The address serves the bytes back.
    served = client.get(body["url"])
    assert served.status_code == 200
    assert served.content[:2] == b"\xff\xd8"  # JPEG start of image


def test_two_uploads_never_share_a_name(client: TestClient) -> None:
    headers = designer(client, "twice@example.com")

    first = client.post(
        "/api/images",
        headers=headers,
        files={"file": ("kitchen.jpg", photo_bytes(), "image/jpeg")},
    ).json()
    second = client.post(
        "/api/images",
        headers=headers,
        files={"file": ("kitchen.jpg", photo_bytes((10, 20, 30)), "image/jpeg")},
    ).json()

    assert first["url"] != second["url"]


def test_a_text_file_renamed_as_a_photo_is_refused(client: TestClient) -> None:
    headers = designer(client, "renamed@example.com")

    response = client.post(
        "/api/images",
        headers=headers,
        files={"file": ("notes.jpg", b"this is not a picture", "image/jpeg")},
    )

    assert response.status_code == 422
    assert "not an image" in response.json()["detail"]


def test_an_upload_needs_an_account(client: TestClient) -> None:
    response = client.post(
        "/api/images",
        files={"file": ("room.jpg", photo_bytes(), "image/jpeg")},
    )

    assert response.status_code == 401
