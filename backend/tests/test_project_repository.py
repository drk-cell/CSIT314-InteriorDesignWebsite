"""The project store answers owner and company queries."""

from __future__ import annotations

from app.domain.project import Project
from app.repositories.project_repository import ProjectRepository


def make_project(owner_id: str, company_id: str, title: str) -> Project:
    return Project(
        owner_id=owner_id,
        company_id=company_id,
        title=title,
        style="Minimal",
        category="Living Room",
        budget_min=10000,
        budget_max=20000,
    )


def test_add_and_get() -> None:
    repository = ProjectRepository()
    project = make_project("account-1", "company-1", "Living Room")

    assert repository.add(project) is True
    assert repository.get(project.id) is project
    assert repository.count() == 1


def test_a_repeated_id_is_refused() -> None:
    repository = ProjectRepository()
    project = make_project("account-1", "company-1", "Living Room")
    repository.add(project)

    assert repository.add(project) is False
    assert repository.count() == 1


def test_list_by_owner_returns_only_that_designer() -> None:
    repository = ProjectRepository()
    repository.add(make_project("account-1", "company-1", "Living Room"))
    repository.add(make_project("account-1", "company-1", "Bedroom"))
    repository.add(make_project("account-2", "company-2", "Kitchen"))

    titles = [project.title for project in repository.list_by_owner("account-1")]

    assert sorted(titles) == ["Bedroom", "Living Room"]


def test_clear_empties_the_store() -> None:
    repository = ProjectRepository()
    repository.add(make_project("account-1", "company-1", "Living Room"))

    repository.clear()

    assert repository.count() == 0
    assert repository.list_all() == []