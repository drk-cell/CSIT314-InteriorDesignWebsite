"""Project reports: a customer complains, platform staff act or dismiss.

Rules that matter:

* Only a customer reports a project, and only one open report per project.
* Only platform staff read the report list.
* Staff may take the project down, suspend the designer, do both, or dismiss.
* Closing a report records whether anything was done, so the list is an audit.
"""

from __future__ import annotations

from app.domain.account import Account
from app.domain.enums import PRIVILEGED_ROLES, ProjectStatus, Role
from app.domain.errors import (
    AccountNotFound,
    InvalidState,
    NotPermitted,
    ProjectNotFound,
    ReportNotFound,
)
from app.domain.report import ProjectReport
from app.repositories.account_repository import AccountRepository
from app.repositories.project_repository import ProjectRepository
from app.repositories.report_repository import ReportRepository


class ProjectReportService:
    """Applies the reporting rules on top of the three stores."""

    def __init__(
        self,
        reports: ReportRepository,
        projects: ProjectRepository,
        accounts: AccountRepository,
    ) -> None:
        self._reports = reports
        self._projects = projects
        self._accounts = accounts

    def submit(
        self, actor: Account, project_id: str, reason: str, comments: str = ""
    ) -> ProjectReport:
        """Record one customer complaint about one project."""
        if actor.role is not Role.CUSTOMER:
            raise NotPermitted("Only a customer may report a project")
        project = self._projects.get(project_id)
        if project is None:
            raise ProjectNotFound()
        if project.status is ProjectStatus.TAKEN_DOWN:
            raise InvalidState("This project is already under review")
        for existing in self._reports.list_by_customer(actor.id):
            if existing.project_id == project.id and existing.is_open:
                raise InvalidState("You already reported this project")
        report = ProjectReport(
            customer_id=actor.id,
            project_id=project.id,
            reason=reason,
            comments=comments,
        )
        self._reports.add(report)
        return report

    def list_reports(self, actor: Account) -> list[ProjectReport]:
        """Return every report, newest first, for platform staff."""
        self._require_staff(actor)
        return sorted(
            self._reports.list_all(), key=lambda entry: entry.created_at, reverse=True
        )

    def resolve(
        self,
        actor: Account,
        report_id: str,
        *,
        take_down: bool = False,
        suspend_designer: bool = False,
    ) -> ProjectReport:
        """Close one report, after the chosen actions.

        No action means the report is dismissed. The project is read once, so
        both actions apply to the same designer.
        """
        self._require_staff(actor)
        report = self._reports.get(report_id)
        if report is None:
            raise ReportNotFound()
        if not report.is_open:
            raise InvalidState("This report is already closed")
        project = self._projects.get(report.project_id)
        if project is None:
            raise ProjectNotFound()
        if take_down:
            project.mark_taken_down()
        if suspend_designer:
            designer = self._accounts.get(project.owner_id)
            if designer is None:
                raise AccountNotFound()
            designer.suspend()
        report.close(actioned=take_down or suspend_designer)
        return report

    # --- reading, for the staff list -------------------------------------

    def project_title(self, report: ProjectReport) -> str:
        """Return the project title the administrator reads."""
        project = self._projects.get(report.project_id)
        return "" if project is None else project.title

    def designer_of(self, report: ProjectReport) -> Account | None:
        """Return the account that published the reported project."""
        project = self._projects.get(report.project_id)
        if project is None:
            return None
        return self._accounts.get(project.owner_id)

    def customer_of(self, report: ProjectReport) -> Account | None:
        """Return the account that raised the report."""
        return self._accounts.get(report.customer_id)

    @staticmethod
    def _require_staff(actor: Account) -> None:
        if actor.role not in PRIVILEGED_ROLES:
            raise NotPermitted("Only platform staff may read or resolve reports")
