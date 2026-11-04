"""The project service applies the portfolio rules."""

from __future__ import annotations

import pytest

from app.domain.enums import ProjectStatus, Role
from app.domain.errors import CompanyNotFound, NotPermitted, ProjectNotFound
from app.services.account_service import AccountService
from app.services.company_service import CompanyService
from app.services.project_service import ProjectService

PASSWORD = "secret123"


def designer_with_company(
    accounts: AccountService, companies: CompanyService, email: str = "dana@example.com"
):
    owner = accounts.register(email, PASSWORD, "Dana Studio", Role.DESIGNER)
    owner.activate()
    companies.create(
        owner,
        name=f"Studio {email.split('@')[0]}",
        description="",
        contact_email=email,
        contact_phone="",
        location="Singapore",
    )
    return owner


def sample_project(projects: ProjectService, owner) -> object:
    return projects.create(
        owner,
        title="Warm Minimal Living Room",
        description="A compact flat opened up.",
        style="Minimal",
        category="Living Room",
        budget_min=20000,
        budget_max=40000,
        images=["/portfolio/photos/photo-01.jpg"],
    )


def test_a_designer_without_a_company_cannot_create(
    account_service: AccountService,
    company_service: CompanyService,
    project_service: ProjectService,
) -> None:
    owner = account_service.register("dana@example.com", PASSWORD, "Dana", Role.DESIGNER)
    owner.activate()

    with pytest.raises(CompanyNotFound):
        sample_project(project_service, owner)


def test_a_customer_cannot_create(
    account_service: AccountService,
    company_service: CompanyService,
    project_service: ProjectService,
) -> None:
    shopper = account_service.register("casey@example.com", PASSWORD, "Casey", Role.CUSTOMER)

    with pytest.raises(NotPermitted):
        sample_project(project_service, shopper)


def test_create_stores_owner_company_and_images(
    account_service: AccountService,
    company_service: CompanyService,
    project_service: ProjectService,
) -> None:
    owner = designer_with_company(account_service, company_service)

    project = sample_project(project_service, owner)

    assert project.is_owned_by(owner.id) is True
    assert project.company_id
    assert project.images == ["/portfolio/photos/photo-01.jpg"]
    assert project_service.get(project.id) is project


def test_any_caller_reads_a_project(
    account_service: AccountService,
    company_service: CompanyService,
    project_service: ProjectService,
) -> None:
    owner = designer_with_company(account_service, company_service)
    project = sample_project(project_service, owner)

    assert project_service.get(project.id).title == "Warm Minimal Living Room"


def test_reading_an_unknown_project_is_a_not_found(project_service: ProjectService) -> None:
    with pytest.raises(ProjectNotFound):
        project_service.get("does-not-exist")


def test_the_owner_updates_one_field(
    account_service: AccountService,
    company_service: CompanyService,
    project_service: ProjectService,
) -> None:
    owner = designer_with_company(account_service, company_service)
    project = sample_project(project_service, owner)

    updated = project_service.update(owner, project.id, title="Quiet Living Room")

    assert updated.title == "Quiet Living Room"
    assert updated.category == "Living Room"


def test_the_owner_moves_a_project_to_past(
    account_service: AccountService,
    company_service: CompanyService,
    project_service: ProjectService,
) -> None:
    owner = designer_with_company(account_service, company_service)
    project = sample_project(project_service, owner)

    updated = project_service.update(owner, project.id, status=ProjectStatus.PAST)

    assert updated.status is ProjectStatus.PAST


def test_another_designer_cannot_update(
    account_service: AccountService,
    company_service: CompanyService,
    project_service: ProjectService,
) -> None:
    owner = designer_with_company(account_service, company_service)
    stranger = designer_with_company(account_service, company_service, "other@example.com")
    project = sample_project(project_service, owner)

    with pytest.raises(NotPermitted):
        project_service.update(stranger, project.id, title="Hijacked")


def test_the_owner_deletes_and_a_stranger_cannot(
    account_service: AccountService,
    company_service: CompanyService,
    project_service: ProjectService,
) -> None:
    owner = designer_with_company(account_service, company_service)
    stranger = designer_with_company(account_service, company_service, "other@example.com")
    project = sample_project(project_service, owner)

    with pytest.raises(NotPermitted):
        project_service.delete(stranger, project.id)

    project_service.delete(owner, project.id)

    with pytest.raises(ProjectNotFound):
        project_service.get(project.id)


def test_the_owner_filters_the_portfolio_by_status(
    account_service: AccountService,
    company_service: CompanyService,
    project_service: ProjectService,
) -> None:
    owner = designer_with_company(account_service, company_service)
    first = sample_project(project_service, owner)
    second = sample_project(project_service, owner)
    project_service.update(owner, second.id, status=ProjectStatus.PAST)

    current = project_service.list_for_owner(owner, ProjectStatus.CURRENT)

    assert [project.id for project in current] == [first.id]


def test_a_company_lists_its_projects(
    account_service: AccountService,
    company_service: CompanyService,
    project_service: ProjectService,
) -> None:
    owner = designer_with_company(account_service, company_service)
    project = sample_project(project_service, owner)

    listed = project_service.list_for_company(project.company_id)

    assert [entry.id for entry in listed] == [project.id]
    
def test_owner_filters_projects_by_name_and_status(
    account_service: AccountService,
    company_service: CompanyService,
    project_service: ProjectService,
) -> None:
    owner = designer_with_company(
        account_service,
        company_service,
    )

    other_designer = designer_with_company(
        account_service,
        company_service,
        "another@example.com",
    )

    # Create three projects.
    living = sample_project(project_service, owner)

    bedroom = sample_project(project_service, owner)
    project_service.update(
        owner,
        bedroom.id,
        title="Past Bedroom",
        status=ProjectStatus.PAST,
    )

    # A different designer owns this project.
    sample_project(project_service, other_designer)

    results = project_service.list_for_owner(
        owner,
        status=ProjectStatus.CURRENT,
        name="  LiViNg  ",
    )

    assert [project.id for project in results] == [living.id]
