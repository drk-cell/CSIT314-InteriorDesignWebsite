"""The upload endpoint and the tag-ranked search.

The analyser itself is covered in ``test_project_tags.py``. This file covers the
two things the feature adds for customers: a photo can be uploaded, and a search
can be ranked by how many tags a project shares with it.
"""

from __future__ import annotations

from io import BytesIO
from typing import Any

from fastapi.testclient import TestClient
from PIL import Image, ImageDraw

from app.api.deps import get_account_repository
from app.domain.project import Project, SearchCriteria
from app.services.tag_suggestion_service import suggest_tags


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


def customer(client: TestClient, email: str) -> dict[str, str]:
    return sign_in(
        client,
        {
            "email": email,
            "password": "look4me1",
            "display_name": "Casey",
            "role": "CUSTOMER",
        },
    )


def photo() -> bytes:
    """A picture with several colours, so the palette has five clusters."""
    image = Image.new("RGB", (640, 480))
    draw = ImageDraw.Draw(image)
    bands = [
        (0, 120, (196, 178, 152)),
        (120, 240, (120, 96, 74)),
        (240, 360, (232, 226, 214)),
        (360, 480, (86, 92, 84)),
        (480, 640, (176, 128, 96)),
    ]
    for left, right, colour in bands:
        draw.rectangle([left, 0, right, 480], fill=colour)
    buffer = BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


# --- the upload endpoint --------------------------------------------------


def test_an_upload_needs_an_account(client: TestClient) -> None:
    response = client.post(
        "/api/images/tags", files={"file": ("room.png", photo(), "image/png")}
    )

    assert response.status_code == 401


def test_a_text_file_is_refused(client: TestClient) -> None:
    headers = customer(client, "reader@example.com")

    response = client.post(
        "/api/images/tags",
        files={"file": ("notes.png", b"this is not an image", "image/png")},
        headers=headers,
    )

    assert response.status_code == 422


def test_a_photo_comes_back_with_tags(client: TestClient) -> None:
    headers = customer(client, "seeker@example.com")

    response = client.post(
        "/api/images/tags",
        files={"file": ("room.png", photo(), "image/png")},
        headers=headers,
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["tags"]
    assert len(body["palette"]) == 5
    assert body["width"] == 640
    assert body["engine"] in {"objects and colour", "colour only"}


def test_the_mapping_holds_only_usable_tags() -> None:
    from app.services.object_labels import LABEL_TO_TAG

    tags = set(LABEL_TO_TAG.values())
    assert tags
    assert all(0 < len(tag) <= 40 for tag in tags)
    assert all(tag == tag.strip() and tag == tag.casefold() for tag in tags)


def test_the_colour_stage_still_works_alone() -> None:
    """The analyser must answer when the model is absent."""
    suggestion = suggest_tags(photo())

    assert suggestion.tags
    assert len(suggestion.palette) == 5


# --- tag ranking ---------------------------------------------------------


def test_overlap_counts_a_tag_once_whatever_its_case() -> None:
    project = Project(
        owner_id="owner-1",
        company_id="company-1",
        title="Quiet Room",
        tags=["Sofa", "warm palette"],
    )

    assert project.tag_overlap(["sofa", "SOFA", "warm palette"]) == 2


def test_a_project_without_a_matching_tag_is_excluded() -> None:
    project = Project(owner_id="o", company_id="c", title="Plain")
    criteria = SearchCriteria(tags=["sofa"])

    assert project.matches(criteria) is False


def test_a_mood_tag_alone_does_not_answer_a_specific_search() -> None:
    """A photo of a sofa often comes with "busy detail"; that tag is everywhere."""
    project = Project(
        owner_id="o", company_id="c", title="Plain", tags=["busy detail"]
    )

    assert project.matches(SearchCriteria(tags=["sofa", "busy detail"])) is False


def test_a_mood_only_search_still_matches_on_mood() -> None:
    project = Project(
        owner_id="o", company_id="c", title="Plain", tags=["busy detail"]
    )

    assert project.matches(SearchCriteria(tags=["busy detail"])) is True


def test_an_object_match_outscores_a_mood_match() -> None:
    object_project = Project(owner_id="o", company_id="c", title="A", tags=["sofa"])
    mood_project = Project(
        owner_id="o", company_id="c", title="B", tags=["busy detail"]
    )
    wanted = ["sofa", "busy detail"]

    assert object_project.tag_score(wanted) > mood_project.tag_score(wanted)


def test_search_puts_the_closest_tag_match_first(client: TestClient) -> None:
    headers = customer(client, "sorter@example.com")
    designer = sign_in(
        client,
        {
            "email": "maker@example.com",
            "password": "make4me1",
            "display_name": "Maker",
            "role": "DESIGNER",
        },
    )
    client.post(
        "/api/companies",
        json={"name": "Studio Maker", "contact_email": "maker@example.com"},
        headers=designer,
    )
    for title, tags in (
        ("Both tags", ["sofa", "warm palette"]),
        ("One tag", ["sofa"]),
        ("No tags", ["oak floor"]),
    ):
        created = client.post(
            "/api/projects",
            json={
                "title": title,
                "category": "Living Room",
                "style": "Minimal",
                "budget_min": 2000000,
                "budget_max": 4000000,
                "tags": tags,
            },
            headers=designer,
        )
        assert created.status_code == 201, created.text

    response = client.get(
        "/api/projects/search", params={"tags": "sofa,warm palette"}, headers=headers
    )

    assert response.status_code == 200, response.text
    titles = [item["title"] for item in response.json()["items"]]
    assert titles == ["Both tags", "One tag"]
