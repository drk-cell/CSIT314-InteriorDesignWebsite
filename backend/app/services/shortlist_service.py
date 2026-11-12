"""Shortlist use cases: a customer saves projects to compare later."""

from __future__ import annotations

from app.domain.account import Account
from app.domain.enums import ProjectStatus, Role
from app.domain.errors import NotPermitted, ProjectNotFound
from app.domain.project import Project
from app.domain.shortlist import Shortlist
from app.repositories.project_repository import ProjectRepository
from app.repositories.shortlist_repository import ShortlistRepository


class ShortlistService:
    """Keeps the saved list and the project counters in step."""

    def __init__(
        self,
        shortlists: ShortlistRepository,
        projects: ProjectRepository,
    ) -> None:
        self._shortlists = shortlists
        self._projects = projects

    def add(self, actor: Account, project_id: str) -> Project:
        """Save a project for the caller. Saving twice changes nothing."""
        self._require_customer(actor)
        project = self._projects.get(project_id)
        if project is None or project.status is ProjectStatus.TAKEN_DOWN:
            raise ProjectNotFound()
        shortlist = self._own_list(actor)
        if shortlist.add(project.id):
            project.record_shortlist()
        return project

    def remove(self, actor: Account, project_id: str) -> None:
        """Drop a project from the caller's list."""
        self._require_customer(actor)
        shortlist = self._shortlists.get_by_customer(actor.id)
        if shortlist is None:
            return
        if shortlist.remove(project_id):
            project = self._projects.get(project_id)
            if project is not None:
                project.withdraw_shortlist()

    def list_for(self, actor: Account) -> list[Project]:
        """Return the saved projects, oldest save first, skipping deleted ones."""
        self._require_customer(actor)
        shortlist = self._shortlists.get_by_customer(actor.id)
        if shortlist is None:
            return []
        projects = [self._projects.get(entry) for entry in shortlist.project_ids]
        return [
            project
            for project in projects
            if project is not None and project.status is not ProjectStatus.TAKEN_DOWN
        ]

    def ids_for(self, actor: Account) -> list[str]:
        """Return the saved project ids."""
        self._require_customer(actor)
        shortlist = self._shortlists.get_by_customer(actor.id)
        return list(shortlist.project_ids) if shortlist is not None else []

    def _own_list(self, actor: Account) -> Shortlist:
        shortlist = self._shortlists.get_by_customer(actor.id)
        if shortlist is None:
            shortlist = Shortlist(customer_id=actor.id)
            self._shortlists.add(shortlist)
        return shortlist

    @staticmethod
    def _require_customer(actor: Account) -> None:
        if actor.role is not Role.CUSTOMER:
            raise NotPermitted("Only a customer may save projects")