"""The ProjectReport entity: one customer's complaint about one project.

A report names a fixed reason, so the administrator reads the same vocabulary
every time, plus free comments. Only platform staff close a report, and closing
records whether anything was done.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from uuid import uuid4

from app.domain.enums import ReportStatus

REPORT_REASONS: tuple[str, ...] = (
    "Inappropriate content",
    "Spam or misleading",
    "Copyright concern",
    "Not an interior project",
    "Other",
)

MAX_COMMENTS: int = 1000


def _now() -> datetime:
    return datetime.now(timezone.utc)


@dataclass
class ProjectReport:
    """One complaint, from the customer who raised it."""

    customer_id: str
    project_id: str
    reason: str
    comments: str = ""
    status: ReportStatus = ReportStatus.OPEN
    created_at: datetime = field(default_factory=_now)
    resolved_at: datetime | None = None
    id: str = field(default_factory=lambda: str(uuid4()))

    def __post_init__(self) -> None:
        """Check the identifiers, the reason and the comments."""
        if not self.customer_id.strip():
            raise ValueError("A report needs a customer")
        if not self.project_id.strip():
            raise ValueError("A report needs a project")
        self.reason = self.reason.strip()
        if self.reason not in REPORT_REASONS:
            raise ValueError("Choose one of the listed reasons")
        self.comments = self.comments.strip()
        if len(self.comments) > MAX_COMMENTS:
            raise ValueError(
                f"Comments must be {MAX_COMMENTS} characters or fewer"
            )

    @property
    def is_open(self) -> bool:
        """Return ``True`` until staff close the report."""
        return self.status is ReportStatus.OPEN

    def close(self, actioned: bool) -> None:
        """Close the report, with a note of whether anything was done."""
        if self.status is not ReportStatus.OPEN:
            raise ValueError("This report is already closed")
        self.status = ReportStatus.ACTIONED if actioned else ReportStatus.DISMISSED
        self.resolved_at = _now()
