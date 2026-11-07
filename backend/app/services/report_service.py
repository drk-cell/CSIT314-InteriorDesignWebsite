"""Activity reports in daily, weekly and monthly buckets.

Counts come from the timestamps the entities already keep. No new store and no
scheduler: a bucket is computed on read, so a report is always current.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from app.repositories.account_repository import AccountRepository
from app.repositories.project_repository import ProjectRepository
from app.repositories.quote_repository import QuoteRepository, QuoteRequestRepository

PERIODS: tuple[str, ...] = ("daily", "weekly", "monthly")
DEFAULT_BUCKETS: int = 12
MAX_BUCKETS: int = 52


@dataclass(frozen=True)
class Bucket:
    """One period of activity."""

    label: str
    start: datetime
    end: datetime
    accounts: int
    projects: int
    quote_requests: int
    quotes: int


@dataclass(frozen=True)
class Report:
    """A period choice and the buckets it produced."""

    period: str
    buckets: list[Bucket]


class ReportService:
    """Builds reports from the four stores that hold timestamps."""

    def __init__(
        self,
        accounts: AccountRepository,
        projects: ProjectRepository,
        requests: QuoteRequestRepository,
        quotes: QuoteRepository,
    ) -> None:
        self._accounts = accounts
        self._projects = projects
        self._requests = requests
        self._quotes = quotes

    def build(
        self, period: str = "daily", buckets: int = DEFAULT_BUCKETS, now: datetime | None = None
    ) -> Report:
        """Return the last ``buckets`` periods, oldest first."""
        if period not in PERIODS:
            raise ValueError(f"Period must be one of {', '.join(PERIODS)}")
        if buckets < 1 or buckets > MAX_BUCKETS:
            raise ValueError(f"Buckets must sit between 1 and {MAX_BUCKETS}")

        moment = now or datetime.now(timezone.utc)
        windows = self._windows(period, buckets, moment)
        accounts = self._accounts.list_all()
        projects = self._projects.list_all()
        requests = self._requests.list_all()
        quotes = self._quotes.list_all()

        result = [
            Bucket(
                label=self._label(period, start),
                start=start,
                end=end,
                accounts=self._count(accounts, start, end),
                projects=self._count(projects, start, end),
                quote_requests=self._count(requests, start, end),
                quotes=self._count(quotes, start, end),
            )
            for start, end in windows
        ]
        return Report(period=period, buckets=result)

    @staticmethod
    def _count(records: list, start: datetime, end: datetime) -> int:
        return sum(1 for record in records if start <= record.created_at < end)

    @staticmethod
    def _windows(period: str, buckets: int, now: datetime) -> list[tuple[datetime, datetime]]:
        """Return ``buckets`` windows, oldest first, ending at ``now``."""
        windows: list[tuple[datetime, datetime]] = []
        cursor = ReportService._floor(period, now)
        for _ in range(buckets):
            start = ReportService._shift(period, cursor, -1)
            windows.append((start, cursor))
            cursor = start
        windows.reverse()
        windows[-1] = (windows[-1][0], now + timedelta(microseconds=1))
        return windows

    @staticmethod
    def _floor(period: str, moment: datetime) -> datetime:
        midnight = moment.replace(hour=0, minute=0, second=0, microsecond=0)
        if period == "daily":
            return midnight + timedelta(days=1)
        if period == "weekly":
            start_of_week = midnight - timedelta(days=midnight.weekday())
            return start_of_week + timedelta(days=7)
        first = midnight.replace(day=1)
        return (first + timedelta(days=32)).replace(day=1)

    @staticmethod
    def _shift(period: str, moment: datetime, count: int) -> datetime:
        if period == "daily":
            return moment + timedelta(days=count)
        if period == "weekly":
            return moment + timedelta(weeks=count)
        month = moment.month - 1 + count
        year = moment.year + month // 12
        month = month % 12 + 1
        return moment.replace(year=year, month=month, day=1)

    @staticmethod
    def _label(period: str, start: datetime) -> str:
        if period == "daily":
            return start.strftime("%Y-%m-%d")
        if period == "weekly":
            iso = start.isocalendar()
            return f"{iso.year}-W{iso.week:02d}"
        return start.strftime("%Y-%m")