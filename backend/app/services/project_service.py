"""Project use cases: publish, edit, delete and list a portfolio."""

from __future__ import annotations

from app.domain.account import Account
from app.domain.enums import PRIVILEGED_ROLES, ProjectStatus, Role
from app.domain.errors import CompanyNotFound, NotPermitted, ProjectNotFound
from app.domain.project import Project
from app.repositories.company_repository import CompanyRepository
from app.repositories.project_repository import ProjectRepository


class ProjectService:
    """Applies the portfolio rules on top of the two stores."""

    def __init__(
        self,
        projects: ProjectRepository,
        companies: CompanyRepository,
    ) -> None:
        self._projects = projects
        self._companies = companies

    def create(
        self,
        actor: Account,
        *,
        title: str,
        description: str,
        style: str,
        category: str,
        budget_min: int,
        budget_max: int,
        images: list[str] | None = None,
        tags: list[str] | None = None,
    ) -> Project:
        """Publish a project under the caller's company.

        A designer must have a company first, because every project is shown
        under one.
        """
        self._require_designer(actor)
        company = self._companies.get_by_owner(actor.id)
        if company is None:
            raise CompanyNotFound()
        project = Project(
            owner_id=actor.id,
            company_id=company.id,
            title=title,
            description=description,
            style=style,
            category=category,
            budget_min=budget_min,
            budget_max=budget_max,
        )
        for url in images or []:
            project.add_image(url)
        for tag in tags or []:
            project.add_tag(tag)
        self._projects.add(project)
        return project

    def get(self, project_id: str, viewer: Account | None = None) -> Project:
        """Return a project by id.

        A taken down project reads as missing to everyone except its owner and
        platform staff, so a report does not leave a public record behind.
        """
        project = self._projects.get(project_id)
        if project is None:
            raise ProjectNotFound()
        if project.status is ProjectStatus.TAKEN_DOWN and not self._may_read_hidden(
            project, viewer
        ):
            raise ProjectNotFound()
        return project

    def update(
        self,
        actor: Account,
        project_id: str,
        *,
        title: str | None = None,
        description: str | None = None,
        style: str | None = None,
        category: str | None = None,
        budget_min: int | None = None,
        budget_max: int | None = None,
        status: ProjectStatus | None = None,
        images: list[str] | None = None,
        tags: list[str] | None = None,
    ) -> Project:
        """Change only the fields that were supplied. Owner only."""
        project = self._require_owned(actor, project_id)
        if title is not None:
            project.rename(title)
        if any(
            value is not None
            for value in (description, style, category, budget_min, budget_max)
        ):
            project.update_details(
                description=description if description is not None else project.description,
                style=style if style is not None else project.style,
                category=category if category is not None else project.category,
                budget_min=budget_min if budget_min is not None else project.budget_min,
                budget_max=budget_max if budget_max is not None else project.budget_max,
            )
        if status is ProjectStatus.TAKEN_DOWN:
            raise NotPermitted("Only platform staff may take a project down")
        if project.status is ProjectStatus.TAKEN_DOWN and status is not None:
            raise NotPermitted(
                "A taken down project can only be restored by platform staff"
            )
        if status is ProjectStatus.PAST:
            project.mark_past()
        elif status is ProjectStatus.CURRENT:
            project.mark_current()
        if images is not None:
            project.replace_images(images)
        if tags is not None:
            project.replace_tags(tags)
        return project

    def require_owned(self, actor: Account, project_id: str) -> Project:
        """Return the project only when the caller owns it."""
        return self._require_owned(actor, project_id)

    def delete(self, actor: Account, project_id: str) -> None:
        """Remove a project. Owner only."""
        project = self._require_owned(actor, project_id)
        self._projects.remove(project.id)

    def list_for_owner(
        self,
        actor: Account,
        status: ProjectStatus | None = None,
        name: str = "",
    ) -> list[Project]:
        """List the owner's projects, optionally filtered by status and title."""

        # Only designers are allowed to manage portfolios.
        self._require_designer(actor)

        # Get only projects belonging to the logged-in designer.
        projects = self._projects.list_by_owner(actor.id)

        # Filter by status, if one was selected.
        if status is not None:
            projects = [
                project
                for project in projects
                if project.status is status
            ]

        # Filter by project title, ignoring uppercase/lowercase.
        search_name = name.strip().casefold()

        if search_name:
            projects = [
                project
                for project in projects
                if search_name in project.title.casefold()
            ]

        # Show newest projects first.
        return sorted(
            projects,
            key=lambda project: project.created_at,
            reverse=True,
        )

    def list_for_company(self, company_id: str) -> list[Project]:
        """Return the projects published under one company, newest first."""
        return sorted(
            self._projects.list_by_company(company_id),
            key=lambda project: project.created_at,
            reverse=True,
        )

    @staticmethod
    def _may_read_hidden(project: Project, viewer: Account | None) -> bool:
        """Return ``True`` when ``viewer`` may still read a taken down project."""
        if viewer is None:
            return False
        if viewer.role in PRIVILEGED_ROLES:
            return True
        return project.is_owned_by(viewer.id)

    @staticmethod
    def _require_designer(actor: Account) -> None:
        if actor.role is not Role.DESIGNER:
            raise NotPermitted("Only an interior designer may manage projects")

    def _require_owned(self, actor: Account, project_id: str) -> Project:
        self._require_designer(actor)
        project = self._projects.get(project_id)
        if project is None:
            raise ProjectNotFound()
        if not project.is_owned_by(actor.id):
            raise NotPermitted("You may only change your own projects")
        return project