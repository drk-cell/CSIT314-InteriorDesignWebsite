"""Tags: entity rules, the analyser, the guard and the endpoint."""

from __future__ import annotations

from io import BytesIO
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient
from PIL import Image

from app.api.deps import get_account_repository
from app.domain.project import MAX_TAGS, Project
from app.services.image_source import ImageUnavailable, load_image_bytes
from app.services.tag_suggestion_service import suggest_tags
from app.domain.project import SearchCriteria

PUBLIC = Path(__file__).resolve().parents[2] / "frontend" / "public"
PHOTO = "/portfolio/photos/photo-01.jpg"


def image_bytes(colour: tuple[int, int, int], size: tuple[int, int] = (400, 300)) -> bytes:
    buffer = BytesIO()
    Image.new("RGB", size, colour).save(buffer, format="PNG")
    return buffer.getvalue()


def make_project(**overrides: Any) -> Project:
    values: dict[str, Any] = {
        "owner_id": "owner-1",
        "company_id": "company-1",
        "title": "Warm Living Room",
    }
    values.update(overrides)
    return Project(**values)


# --- entity ---------------------------------------------------------------


def test_tags_deduplicate_ignoring_case() -> None:
    project = make_project(tags=["Warm", "warm", "Bright"])

    assert project.tags == ["Warm", "Bright"]


def test_tags_are_bounded() -> None:
    with pytest.raises(ValueError):
        make_project(tags=[f"tag {index}" for index in range(MAX_TAGS + 1)])


def test_a_long_tag_is_rejected() -> None:
    with pytest.raises(ValueError):
        make_project(tags=["x" * 41])


def test_blank_tags_are_dropped() -> None:
    project = make_project(tags=["  ", "Bright", ""])

    assert project.tags == ["Bright"]


def test_replace_and_remove_tags() -> None:
    project = make_project(tags=["Warm"])
    project.replace_tags(["Bright", "Calm"])
    project.remove_tag("bright")

    assert project.tags == ["Calm"]


def test_the_keyword_matches_a_tag() -> None:
    project = make_project(tags=["warm neutrals"], description="")

    assert project.matches(SearchCriteria(keyword="neutrals"))
    assert not project.matches(SearchCriteria(keyword="industrial"))


# --- analyser -------------------------------------------------------------


def test_a_bright_photo_reads_bright() -> None:
    suggestion = suggest_tags(image_bytes((250, 250, 250)))

    assert "bright" in suggestion.tags
    assert "neutral palette" in suggestion.tags


def test_a_dark_photo_reads_moody() -> None:
    suggestion = suggest_tags(image_bytes((12, 10, 10)))

    assert "moody" in suggestion.tags


def test_the_palette_holds_five_shares_that_add_up() -> None:
    suggestion = suggest_tags(load_image_bytes(PHOTO, PUBLIC))

    assert len(suggestion.palette) == 5
    assert sum(entry.percent for entry in suggestion.palette) == pytest.approx(100, abs=1.0)
    assert all(entry.hex.startswith("#") and len(entry.hex) == 7 for entry in suggestion.palette)


def test_the_size_is_reported() -> None:
    suggestion = suggest_tags(image_bytes((200, 200, 200), size=(640, 480)))

    assert (suggestion.width, suggestion.height) == (640, 480)


def test_bytes_that_are_not_an_image_are_refused() -> None:
    with pytest.raises(ValueError):
        suggest_tags(b"not an image at all")


# --- guard ----------------------------------------------------------------


def test_a_public_photo_is_read() -> None:
    data = load_image_bytes(PHOTO, PUBLIC)

    assert data[:2] == b"\xff\xd8"  # JPEG start of image


def test_a_path_that_leaves_the_folder_is_refused() -> None:
    with pytest.raises(ImageUnavailable):
        load_image_bytes("/../backend/app/main.py", PUBLIC)


def test_loopback_and_file_addresses_are_refused() -> None:
    with pytest.raises(ImageUnavailable):
        load_image_bytes("http://127.0.0.1/photo.jpg", PUBLIC)
    with pytest.raises(ImageUnavailable):
        load_image_bytes("file:///C:/Windows/win.ini", PUBLIC)


# --- endpoint -------------------------------------------------------------


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


def publish(client: TestClient, headers: dict[str, str], **overrides: Any) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "title": "Warm Living Room",
        "style": "Minimal",
        "category": "Living Room",
        "budget_min": 20000,
        "budget_max": 40000,
        "images": [PHOTO],
        "tags": ["warm neutrals"],
    }
    payload.update(overrides)
    response = client.post("/api/projects", json=payload, headers=headers)
    assert response.status_code == 201, response.text
    return response.json()


def test_tags_survive_create_and_patch(client: TestClient) -> None:
    headers = designer(client, "dana@example.com")

    created = publish(client, headers, tags=["warm neutrals", "bright"])
    patched = client.patch(
        f"/api/projects/{created['id']}",
        json={"tags": ["quiet", "oak"]},
        headers=headers,
    )

    assert created["tags"] == ["warm neutrals", "bright"]
    assert patched.status_code == 200
    assert patched.json()["tags"] == ["quiet", "oak"]


def test_the_owner_gets_tag_suggestions(client: TestClient) -> None:
    headers = designer(client, "dana@example.com")
    project = publish(client, headers)

    response = client.post(f"/api/projects/{project['id']}/suggest-tags", headers=headers)

    assert response.status_code == 200, response.text
    body = response.json()
    assert set(body) == {
        "palette",
        "tags",
        "width",
        "height",
        "engine",
        "subject",
        "objects",
    }
    assert len(body["palette"]) == 5
    assert body["tags"]
    assert body["engine"] in {"objects and colour", "colour only"}
    assert body["subject"] in {"room", "other"}


def test_another_designer_cannot_ask_for_suggestions(client: TestClient) -> None:
    owner = designer(client, "dana@example.com")
    stranger = designer(client, "other@example.com")
    project = publish(client, owner)

    response = client.post(f"/api/projects/{project['id']}/suggest-tags", headers=stranger)

    assert response.status_code == 403


def test_a_project_without_a_photo_says_so(client: TestClient) -> None:
    headers = designer(client, "dana@example.com")
    project = publish(client, headers, images=[])

    response = client.post(f"/api/projects/{project['id']}/suggest-tags", headers=headers)

    assert response.status_code == 400
    assert response.json()["detail"] == "The project has no photo to analyse"


def test_a_photo_index_that_does_not_exist_is_refused(client: TestClient) -> None:
    headers = designer(client, "dana@example.com")
    project = publish(client, headers)

    response = client.post(
        f"/api/projects/{project['id']}/suggest-tags?image_index=4", headers=headers
    )

    assert response.status_code == 400


def test_a_customer_search_finds_the_tag(client: TestClient) -> None:
    headers = designer(client, "dana@example.com")
    publish(client, headers, tags=["warm neutrals"])
    shopper = sign_in(
        client,
        {
            "email": "casey@example.com",
            "password": "design4me",
            "display_name": "Casey",
            "role": "CUSTOMER",
        },
    )

    response = client.get("/api/projects/search?keyword=neutrals", headers=shopper)

    assert response.status_code == 200
    assert response.json()["total"] == 1