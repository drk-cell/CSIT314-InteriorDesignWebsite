"""Import the tester data files into a running backend.

Reads the four CSV files in ``testing/data`` and creates the records through the
public API, in dependency order: accounts, companies, projects, quote requests.

Every row is checked before it is sent, so a mistake in the file is reported as
"line 7, column budget_min, floor above ceiling" instead of a server error. A
row that the server refuses is reported with the server's own message.

Usage, from the repository root, with the app already started:

    backend/.venv/Scripts/python.exe backend/scripts/import_data.py

Options:

    --dir PATH      folder holding the CSV files (default testing/data)
    --dry-run       check the files and print the report, send nothing
    --report PATH   write the report to this file as well

Exit code is 0 when every row was accepted, 1 when any row was rejected.
"""

from __future__ import annotations

import argparse
import csv
import os
import sys
from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation
from pathlib import Path

import httpx

BASE = os.environ.get("DEMO_BASE", "http://127.0.0.1:8000/api")
ADMIN_EMAIL = os.environ.get("APP_ADMIN_EMAIL", "admin@example.com")
ADMIN_PASSWORD = os.environ.get("APP_ADMIN_PASSWORD", "passw0rd123")
DEFAULT_PASSWORD = "passw0rd123"
MAX_IMAGES = 8
MAX_TAGS = 12


@dataclass
class RowResult:
    """One row's outcome."""

    file: str
    line: int
    accepted: bool
    detail: str = ""
    skipped: bool = False


@dataclass
class Report:
    """Every outcome, in file order."""

    rows: list[RowResult] = field(default_factory=list)

    def accept(self, name: str, line: int) -> None:
        self.rows.append(RowResult(name, line, True))

    def skip(self, name: str, line: int, detail: str) -> None:
        self.rows.append(RowResult(name, line, True, detail, skipped=True))

    def reject(self, name: str, line: int, detail: str) -> None:
        self.rows.append(RowResult(name, line, False, detail))

    def summary(self) -> list[tuple[str, int, int, int]]:
        files: list[str] = []
        for row in self.rows:
            if row.file not in files:
                files.append(row.file)
        return [
            (
                name,
                sum(1 for row in self.rows if row.file == name and row.accepted and not row.skipped),
                sum(1 for row in self.rows if row.file == name and row.skipped),
                sum(1 for row in self.rows if row.file == name and not row.accepted),
            )
            for name in files
        ]

    def failures(self) -> list[RowResult]:
        return [row for row in self.rows if not row.accepted]


def money(value: str, column: str) -> int:
    """Read dollars and return cents. Accepts 25000, 25,000 and 25,000.50."""
    text = value.strip().replace(",", "").replace("$", "").replace("S", "")
    if text == "":
        raise ValueError(f"{column} is empty")
    try:
        amount = Decimal(text)
    except InvalidOperation as exc:
        raise ValueError(f"{column} is not a number: {value!r}") from exc
    if amount < 0:
        raise ValueError(f"{column} is negative")
    if amount > Decimal("1000000"):
        raise ValueError(f"{column} is above one million dollars")
    return int(amount * 100)


def yes(value: str) -> bool:
    return value.strip().upper() in ("YES", "Y", "TRUE", "1")


def split_list(value: str) -> list[str]:
    return [entry.strip() for entry in value.split(";") if entry.strip()]


def read_rows(path: Path) -> list[tuple[int, dict[str, str]]]:
    """Return the data rows with their file line numbers, skipping notes.

    A row with more values than the header is kept, marked with ``_error``, so
    the report can name the line instead of the whole run crashing.
    """
    if not path.exists():
        return []
    rows: list[tuple[int, dict[str, str]]] = []
    with path.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None:
            return []
        for index, raw in enumerate(reader, start=2):
            if raw is None:
                continue
            cleaned = {
                (key or "").strip(): (value if isinstance(value, str) else "")
                for key, value in raw.items()
                if key is not None
            }
            cleaned = {key: value.strip() for key, value in cleaned.items()}
            first = (cleaned.get(reader.fieldnames[0]) or "").strip()
            if first == "" or first.startswith("#"):
                continue
            if None in raw:
                cleaned["_error"] = (
                    "the row has more values than the header; "
                    "a comma inside a field needs double quotes"
                )
            rows.append((index, cleaned))
    return rows


def clean_rows(
    report: "Report", name: str, rows: list[tuple[int, dict[str, str]]]
) -> list[tuple[int, dict[str, str]]]:
    """Reject the rows that cannot be read, and return the rest."""
    good: list[tuple[int, dict[str, str]]] = []
    for line, row in rows:
        if "_error" in row:
            report.reject(name, line, row["_error"])
        else:
            good.append((line, row))
    return good


class Importer:
    """Creates the records through the API and keeps the ids it learns."""

    def __init__(self, client: httpx.Client, report: Report, dry_run: bool) -> None:
        self.client = client
        self.report = report
        self.dry_run = dry_run
        self.tokens: dict[str, str] = {}
        self.account_ids: dict[str, str] = {}
        self.companies: dict[str, dict] = {}
        self.company_owner: dict[str, str] = {}
        self.known_emails: set[str] = set()
        self.categories: list[str] = []
        self.styles: list[str] = []

    # --- helpers ---------------------------------------------------------

    def login(self, email: str, password: str = DEFAULT_PASSWORD) -> str | None:
        if email in self.tokens:
            return self.tokens[email]
        response = self.client.post(
            "/auth/login", json={"email": email, "password": password}
        )
        if response.status_code != 200:
            return None
        token = response.json()["access_token"]
        self.tokens[email] = token
        return token

    def register(self, email: str, name: str, role: str, password: str) -> tuple[str, bool]:
        """Create the account, or find it. Returns the id and whether it is new."""
        response = self.client.post(
            "/auth/register",
            json={
                "email": email,
                "password": password,
                "display_name": name,
                "role": role,
            },
        )
        if response.status_code == 201:
            return response.json()["id"], True
        if response.status_code == 409:
            existing = self.login(email, password)
            if existing is None:
                raise ValueError(
                    "the account already exists with another password"
                )
            me = self.client.get("/auth/me", headers={"Authorization": f"Bearer {existing}"})
            if me.status_code != 200:
                raise ValueError("the account exists but cannot be read")
            return me.json()["id"], False
        raise ValueError(self._detail(response))

    @staticmethod
    def _detail(response: httpx.Response) -> str:
        try:
            body = response.json()
        except ValueError:
            return f"server said {response.status_code}"
        detail = body.get("detail") if isinstance(body, dict) else None
        if isinstance(detail, str):
            return detail
        if isinstance(detail, list) and detail:
            first = detail[0]
            if isinstance(first, dict):
                return str(first.get("msg", "invalid value"))
        return f"server said {response.status_code}"

    # --- steps -----------------------------------------------------------

    def load_accounts(self, rows: list[tuple[int, dict[str, str]]]) -> None:
        for line, row in rows:
            email = row.get("email", "")
            name = row.get("display_name", "")
            role = row.get("role", "").upper()
            password = row.get("password", "") or DEFAULT_PASSWORD
            try:
                if "@" not in email:
                    raise ValueError("email does not look like an address")
                if not name:
                    raise ValueError("display_name is empty")
                if role not in ("CUSTOMER", "DESIGNER"):
                    raise ValueError("role must be CUSTOMER or DESIGNER")
                if self.dry_run:
                    self.report.accept("accounts.csv", line)
                    continue
                account_id, created = self.register(email, name, role, password)
                self.account_ids[email] = account_id
                if role == "DESIGNER":
                    self._approve(account_id)
                if self.login(email, password) is None:
                    raise ValueError("the account cannot sign in")
                if created:
                    self.report.accept("accounts.csv", line)
                else:
                    self.report.skip("accounts.csv", line, "already present")
            except Exception as exc:  # noqa: BLE001 - reported per row
                self.report.reject("accounts.csv", line, str(exc))

    def _approve(self, account_id: str) -> None:
        token = self.login(ADMIN_EMAIL, ADMIN_PASSWORD)
        if token is None:
            raise ValueError("cannot sign in as the administrator to approve")
        self.client.post(
            f"/admin/accounts/{account_id}/approve",
            headers={"Authorization": f"Bearer {token}"},
        )

    def load_companies(self, rows: list[tuple[int, dict[str, str]]]) -> None:
        for line, row in rows:
            email = row.get("designer_email", "")
            name = row.get("name", "")
            try:
                if not name:
                    raise ValueError("name is empty")
                if not row.get("contact_email"):
                    raise ValueError("contact_email is empty")
                if self.dry_run:
                    if email not in self.known_emails and self.login(email) is None:
                        raise ValueError(
                            f"{email} is not in accounts.csv and cannot sign in"
                        )
                    self.report.accept("companies.csv", line)
                    continue
                token = self.login(email)
                if token is None:
                    raise ValueError(f"{email} cannot sign in; add it to accounts.csv")
                response = self.client.post(
                    "/companies",
                    headers={"Authorization": f"Bearer {token}"},
                    json={
                        "name": name,
                        "description": row.get("description", ""),
                        "contact_email": row["contact_email"],
                        "contact_phone": row.get("contact_phone", ""),
                        "location": row.get("location", ""),
                        "logo_url": row.get("logo_url", ""),
                    },
                )
                if response.status_code == 201:
                    company = response.json()
                    self.companies[name] = company
                    self.companies[email] = company
                    created = True
                elif response.status_code in (409, 400, 422):
                    company = self._find_company(token, name)
                    if company is None:
                        raise ValueError(self._detail(response))
                    self.companies[name] = company
                    self.companies[email] = company
                    created = False
                else:
                    raise ValueError(self._detail(response))
                if created:
                    self.report.accept("companies.csv", line)
                else:
                    self.report.skip("companies.csv", line, "already present")
            except Exception as exc:  # noqa: BLE001
                self.report.reject("companies.csv", line, str(exc))

    def _find_company(self, token: str, name: str) -> dict | None:
        """Look for an existing company with this name."""
        listing = self.client.get(
            "/companies", headers={"Authorization": f"Bearer {token}"}
        )
        if listing.status_code == 200:
            for entry in listing.json():
                if entry.get("name") == name:
                    return entry
        return None

    def load_projects(self, rows: list[tuple[int, dict[str, str]]]) -> None:
        for line, row in rows:
            email = row.get("designer_email", "")
            title = row.get("title", "")
            try:
                if not title:
                    raise ValueError("title is empty")
                category = row.get("category", "")
                style = row.get("style", "")
                if category and self.categories and category not in self.categories:
                    raise ValueError(
                        f"category {category!r} is not in the list: {', '.join(self.categories)}"
                    )
                if style and self.styles and style not in self.styles:
                    raise ValueError(
                        f"style {style!r} is not in the list: {', '.join(self.styles)}"
                    )
                low = money(row.get("budget_min", ""), "budget_min")
                high = money(row.get("budget_max", ""), "budget_max")
                if low > high:
                    raise ValueError("budget_min is above budget_max")
                images = split_list(row.get("images", ""))
                if len(images) > MAX_IMAGES:
                    raise ValueError(f"{len(images)} images, the limit is {MAX_IMAGES}")
                tags = split_list(row.get("tags", ""))
                if len(tags) > MAX_TAGS:
                    raise ValueError(f"{len(tags)} tags, the limit is {MAX_TAGS}")
                if self.dry_run:
                    if email not in self.known_emails and self.login(email) is None:
                        raise ValueError(
                            f"{email} is not in accounts.csv and cannot sign in"
                        )
                    self.report.accept("projects.csv", line)
                    continue
                token = self.login(email)
                if token is None:
                    raise ValueError(f"{email} cannot sign in; add it to accounts.csv")
                existing = self.client.get(
                    "/projects/mine",
                    params={"name": title},
                    headers={"Authorization": f"Bearer {token}"},
                )
                if existing.status_code == 200 and any(
                    entry.get("title") == title for entry in existing.json()
                ):
                    self.report.skip("projects.csv", line, "already present")
                    continue
                response = self.client.post(
                    "/projects",
                    headers={"Authorization": f"Bearer {token}"},
                    json={
                        "title": title,
                        "description": row.get("description", ""),
                        "category": category,
                        "style": style,
                        "budget_min": low,
                        "budget_max": high,
                        "images": images,
                        "tags": tags,
                    },
                )
                if response.status_code != 201:
                    raise ValueError(self._detail(response))
                project = response.json()
                if row.get("status", "").upper() == "PAST":
                    self.client.patch(
                        f"/projects/{project['id']}",
                        headers={"Authorization": f"Bearer {token}"},
                        json={"status": "PAST"},
                    )
                self.report.accept("projects.csv", line)
            except Exception as exc:  # noqa: BLE001
                self.report.reject("projects.csv", line, str(exc))

    def load_requests(self, rows: list[tuple[int, dict[str, str]]]) -> None:
        for line, row in rows:
            email = row.get("customer_email", "")
            company_name = row.get("company_name", "")
            try:
                title = row.get("title", "")
                scope = row.get("scope", "")
                if not title:
                    raise ValueError("title is empty")
                if not scope:
                    raise ValueError("scope is empty")
                low = money(row.get("budget_min", ""), "budget_min")
                high = money(row.get("budget_max", ""), "budget_max")
                if low > high:
                    raise ValueError("budget_min is above budget_max")
                target = (
                    money(row["target"], "target") if row.get("target", "") else None
                )
                if company_name not in self.company_owner:
                    raise ValueError(
                        f"company {company_name!r} is not in companies.csv"
                    )
                company = self.companies.get(company_name)
                if not self.dry_run and company is None:
                    raise ValueError(
                        f"company {company_name!r} was not created; check its companies.csv row"
                    )
                if self.dry_run:
                    if email not in self.known_emails and self.login(email) is None:
                        raise ValueError(
                            f"{email} is not in accounts.csv and cannot sign in"
                        )
                    self.report.accept("quote_requests.csv", line)
                    continue
                token = self.login(email)
                if token is None:
                    raise ValueError(f"{email} cannot sign in; add it to accounts.csv")
                mailed = self.client.get(
                    "/quotes/requests", headers={"Authorization": f"Bearer {token}"}
                )
                if mailed.status_code == 200 and any(
                    entry.get("title") == title
                    and entry.get("company_id") == company["id"]
                    for entry in mailed.json()
                ):
                    self.report.skip("quote_requests.csv", line, "already present")
                    continue
                response = self.client.post(
                    "/quotes/requests",
                    headers={"Authorization": f"Bearer {token}"},
                    json={
                        "company_id": company["id"],
                        "title": title,
                        "scope": scope,
                        "budget_min_cents": low,
                        "budget_max_cents": high,
                        "target_cents": target,
                    },
                )
                if response.status_code != 201:
                    raise ValueError(self._detail(response))
                request = response.json()
                answer = row.get("answer_total", "")
                if answer:
                    designer_token = self.login(company_designer(self, company_name))
                    if designer_token is None:
                        raise ValueError("cannot sign in as the designer to answer")
                    days = row.get("answer_days", "") or "14"
                    answered = self.client.post(
                        f"/quotes/requests/{request['id']}/quotes",
                        headers={"Authorization": f"Bearer {designer_token}"},
                        json={
                            "total_cents": money(answer, "answer_total"),
                            "valid_days": int(days),
                            "gst_included": yes(row.get("gst_included", "")),
                            "note": "Imported answer",
                        },
                    )
                    if answered.status_code != 201:
                        raise ValueError(self._detail(answered))
                self.report.accept("quote_requests.csv", line)
            except Exception as exc:  # noqa: BLE001
                self.report.reject("quote_requests.csv", line, str(exc))


def company_designer(importer: Importer, company_name: str) -> str:
    """Return the designer email behind a company name, from the CSV rows."""
    return importer.company_owner.get(company_name, "")


def main() -> int:
    parser = argparse.ArgumentParser(description="Import the tester CSV files")
    parser.add_argument("--dir", default=None, help="folder with the CSV files")
    parser.add_argument("--dry-run", action="store_true", help="check only")
    parser.add_argument("--report", default=None, help="also write the report here")
    args = parser.parse_args()

    folder = Path(args.dir) if args.dir else Path(__file__).resolve().parents[2] / "testing" / "data"
    if not folder.is_dir():
        print(f"Cannot find the data folder: {folder}")
        return 1

    report = Report()
    try:
        with httpx.Client(base_url=BASE, timeout=60) as client:
            importer = Importer(client, report, args.dry_run)
            importer.company_owner = {}
            catalogue = client.get("/catalogue")
            if catalogue.status_code == 200:
                body = catalogue.json()
                importer.categories = body.get("categories", [])
                importer.styles = body.get("styles", [])

            accounts = clean_rows(report, "accounts.csv", read_rows(folder / "accounts.csv"))
            companies = clean_rows(report, "companies.csv", read_rows(folder / "companies.csv"))
            importer.known_emails = {
                row.get("email", "") for _line, row in accounts if row.get("email")
            }
            for _line, row in companies:
                importer.company_owner[row.get("name", "")] = row.get(
                    "designer_email", ""
                )

            importer.load_accounts(accounts)
            importer.load_companies(companies)
            importer.load_projects(
                clean_rows(report, "projects.csv", read_rows(folder / "projects.csv"))
            )
            importer.load_requests(
                clean_rows(
                    report,
                    "quote_requests.csv",
                    read_rows(folder / "quote_requests.csv"),
                )
            )
    except httpx.HTTPError as exc:
        print(f"Cannot reach the app at {BASE}. Start it with 3-start-app.bat first.")
        print(f"  {exc}")
        return 1

    lines = []
    for name, accepted, skipped, rejected in report.summary():
        lines.append(
            f"{name:<22}{accepted:>4} accepted {skipped:>4} skipped {rejected:>4} rejected"
        )
    failures = report.failures()
    if failures:
        lines.append("")
        lines.append("Rejected rows:")
        for row in failures:
            lines.append(f"  {row.file} line {row.line}: {row.detail}")
    else:
        lines.append("")
        lines.append("Every row was accepted.")

    text = "\n".join(lines)
    print(text)
    target = Path(args.report) if args.report else folder / "import-report.txt"
    target.write_text(text + "\n", encoding="utf-8")
    return 0 if not failures else 1


if __name__ == "__main__":
    sys.exit(main())