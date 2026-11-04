"""The project entity owns the portfolio rules."""

from __future__ import annotations

import pytest

from app.domain.enums import ProjectStatus
from app.domain.project import Project, SearchCriteria

OWNER = "account-1"
COMPANY = "company-1"


def make_project(**overrides: object) -> Project:
    fields: dict[str, object] = {
        "owner_id": OWNER,
        "company_id": COMPANY,
        "title": "Warm Minimal Living Room",
        "description": "A compact flat opened up.",
        "style": "Minimal",
        "category": "Living Room",
        "budget_min": 20000,
        "budget_max": 40000,
    }
    fields.update(overrides)
    return Project(**fields)  # type: ignore[arg-type]


def test_a_new_project_is_current_and_unread() -> None:
    project = make_project()

    assert project.status is ProjectStatus.CURRENT
    assert project.view_count == 0
    assert project.shortlist_count == 0
    assert project.images == []


def test_a_blank_title_is_rejected() -> None:
    with pytest.raises(ValueError):
        make_project(title="   ")


def test_the_budget_floor_may_not_exceed_the_ceiling() -> None:
    with pytest.raises(ValueError):
        make_project(budget_min=50000, budget_max=20000)


def test_a_negative_budget_is_rejected() -> None:
    with pytest.raises(ValueError):
        make_project(budget_min=-1, budget_max=20000)


def test_rename_trims_and_rejects_blank() -> None:
    project = make_project()

    project.rename("  Quiet Bedroom ")

    assert project.title == "Quiet Bedroom"
    with pytest.raises(ValueError):
        project.rename("   ")


def test_status_moves_between_current_and_past() -> None:
    project = make_project()

    project.mark_past()
    assert project.status is ProjectStatus.PAST

    project.mark_current()
    assert project.status is ProjectStatus.CURRENT


def test_images_are_capped_and_duplicates_are_ignored() -> None:
    project = make_project()

    for index in range(8):
        project.add_image(f"https://cdn.example.com/{index}.svg")
    project.add_image("https://cdn.example.com/0.svg")

    assert len(project.images) == 8
    assert project.images[0] == "https://cdn.example.com/0.svg"
    with pytest.raises(ValueError):
        project.add_image("https://cdn.example.com/8.svg")


def test_a_blank_image_address_is_rejected() -> None:
    project = make_project()

    with pytest.raises(ValueError):
        project.add_image("  ")


def test_an_image_can_be_removed() -> None:
    project = make_project()
    project.add_image("https://cdn.example.com/0.svg")

    project.remove_image("https://cdn.example.com/0.svg")

    assert project.images == []


def test_counters_rise_and_never_fall_below_zero() -> None:
    project = make_project()

    project.record_view()
    project.record_view()
    project.record_shortlist()
    project.withdraw_shortlist()
    project.withdraw_shortlist()

    assert project.view_count == 2
    assert project.shortlist_count == 0


def test_details_are_validated_on_update() -> None:
    project = make_project()

    with pytest.raises(ValueError):
        project.update_details(
            description="x",
            style="",
            category="Living Room",
            budget_min=1000,
            budget_max=2000,
        )


def test_details_update_the_record() -> None:
    project = make_project()
    before = project.updated_at

    project.update_details(
        description="Opened up, warm oak.",
        style="Japandi",
        category="Living Room",
        budget_min=30000,
        budget_max=60000,
    )

    assert project.style == "Japandi"
    assert project.budget_min == 30000
    assert project.updated_at >= before


def test_is_owned_by_compares_the_owner() -> None:
    project = make_project()

    assert project.is_owned_by(OWNER) is True
    assert project.is_owned_by("account-2") is False

def test_matches_accepts_a_project_when_no_criteria_are_given() -> None:
    project = make_project()
    assert project.matches(SearchCriteria()) is True


def test_matches_rejects_a_different_category() -> None:
    project = make_project()
    assert project.matches(SearchCriteria(category="Kitchen")) is False


def test_matches_ignores_the_case_of_the_style() -> None:
    project = make_project()
    assert project.matches(SearchCriteria(style="minimal")) is True


def test_matches_accepts_a_budget_that_overlaps_the_band() -> None:
    project = make_project(budget_min=20000, budget_max=40000)
    assert project.matches(SearchCriteria(budget_min=30000, budget_max=50000)) is True


def test_matches_rejects_a_budget_above_the_band() -> None:
    project = make_project(budget_min=20000, budget_max=40000)
    assert project.matches(SearchCriteria(budget_min=60000, budget_max=80000)) is False


def test_criteria_refuse_a_minimum_above_the_maximum() -> None:
    with pytest.raises(ValueError, match="must not exceed"):
        SearchCriteria(budget_min=50000, budget_max=30000)


def test_criteria_refuse_a_negative_budget() -> None:
    with pytest.raises(ValueError, match="must not be negative"):
        SearchCriteria(budget_min=-1)
