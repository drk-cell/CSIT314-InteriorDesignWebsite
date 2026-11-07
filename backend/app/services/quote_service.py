"""Quote use cases: ask, answer, negotiate on a total, accept or decline.

Rules that matter and are easy to get wrong:

* One open request per customer and company, so a designer is never spammed.
* Only the company behind the request may answer or revise it.
* A customer names a target price; it is a note, not a binding offer.
* Three versions and three counters per request, then the request is frozen.
* Accepting a quote closes that request only. Other requests stay open, because
  closing them is the customer's decision, not a side effect.
"""

from __future__ import annotations

from app.domain.account import Account
from app.domain.enums import PRIVILEGED_ROLES, QuoteRequestState, QuoteState, Role
from app.domain.errors import (
    CompanyNotFound,
    InvalidState,
    NotPermitted,
    ProjectNotFound,
    QuoteNotFound,
    QuoteRequestNotFound,
)
from app.domain.quote import MAX_VERSIONS, Quote
from app.domain.quote_request import QuoteRequest
from app.repositories.company_repository import CompanyRepository
from app.repositories.project_repository import ProjectRepository
from app.repositories.quote_repository import QuoteRepository, QuoteRequestRepository


class QuoteService:
    """Applies the quoting rules on top of the four stores."""

    def __init__(
        self,
        requests: QuoteRequestRepository,
        quotes: QuoteRepository,
        companies: CompanyRepository,
        projects: ProjectRepository,
    ) -> None:
        self._requests = requests
        self._quotes = quotes
        self._companies = companies
        self._projects = projects

    # --- customer side ----------------------------------------------------

    def submit(
        self,
        actor: Account,
        *,
        company_id: str,
        title: str,
        scope: str,
        budget_min_cents: int,
        budget_max_cents: int,
        target_cents: int | None = None,
        project_id: str | None = None,
    ) -> QuoteRequest:
        """Send one request to one company."""
        self._require_customer(actor)
        company = self._companies.get(company_id)
        if company is None:
            raise CompanyNotFound()
        if project_id is not None:
            project = self._projects.get(project_id)
            if project is None:
                raise ProjectNotFound()
            if project.company_id != company.id:
                raise NotPermitted("That project belongs to another company")
        for existing in self._requests.list_by_customer(actor.id):
            if existing.company_id == company.id and existing.is_open:
                raise InvalidState(
                    "You already have an open request with this company"
                )
        request = QuoteRequest(
            customer_id=actor.id,
            company_id=company.id,
            title=title,
            scope=scope,
            budget_min_cents=budget_min_cents,
            budget_max_cents=budget_max_cents,
            target_cents=target_cents,
            project_id=project_id,
        )
        self._requests.add(request)
        return request

    def counter(
        self, actor: Account, request_id: str, target_cents: int, note: str
    ) -> QuoteRequest:
        """Record the price the customer wants and why."""
        request = self._owned_request(actor, request_id)
        try:
            request.counter(target_cents, note)
        except ValueError as exc:
            raise InvalidState(str(exc)) from exc
        return request

    def cancel(self, actor: Account, request_id: str, reason: str = "") -> QuoteRequest:
        """Stop an open request."""
        request = self._owned_request(actor, request_id)
        try:
            request.cancel(reason)
        except ValueError as exc:
            raise InvalidState(str(exc)) from exc
        for quote in self._quotes.list_by_request(request.id):
            quote.expire() if quote.is_expired() else None
        return request

    def accept(self, actor: Account, quote_id: str) -> Quote:
        """Accept one quote. Other requests of this customer stay open."""
        quote, request = self._owned_quote(actor, quote_id)
        if quote.is_expired():
            quote.expire()
            request.expire()
            raise InvalidState("This quote has expired")
        try:
            quote.accept()
            request.accept()
        except ValueError as exc:
            raise InvalidState(str(exc)) from exc
        return quote

    def decline(self, actor: Account, quote_id: str, reason: str = "") -> Quote:
        """Turn one quote down."""
        quote, request = self._owned_quote(actor, quote_id)
        try:
            quote.decline(reason)
            request.decline(reason)
        except ValueError as exc:
            raise InvalidState(str(exc)) from exc
        return quote

    # --- designer side ----------------------------------------------------

    def answer(
        self,
        actor: Account,
        request_id: str,
        *,
        total_cents: int,
        valid_days: int,
        gst_included: bool,
        note: str = "",
    ) -> Quote:
        """Send version one of the quote."""
        request = self._request_for_designer(actor, request_id)
        if request.state is not QuoteRequestState.PENDING:
            raise InvalidState("Only a pending request can be answered")
        try:
            quote = Quote(
                request_id=request.id,
                total_cents=total_cents,
                valid_until=Quote.validity_date(valid_days),
                gst_included=gst_included,
                note=note,
                version=1,
            )
            request.mark_answered()
        except ValueError as exc:
            raise InvalidState(str(exc)) from exc
        self._quotes.add(quote)
        return quote

    def revise(
        self,
        actor: Account,
        quote_id: str,
        *,
        total_cents: int,
        valid_days: int,
        gst_included: bool,
        note: str = "",
    ) -> Quote:
        """Send the next version of the quote."""
        previous = self._quotes.get(quote_id)
        if previous is None:
            raise QuoteNotFound()
        request = self._request_for_designer(actor, previous.request_id)
        if request.state is not QuoteRequestState.ANSWERED:
            raise InvalidState("Only an answered request can be revised")
        if previous.state is not QuoteState.OFFERED:
            raise InvalidState("Only the current version can be revised")
        next_version = previous.version + 1
        if next_version > MAX_VERSIONS:
            raise InvalidState(f"This request reached {MAX_VERSIONS} versions")
        try:
            quote = Quote(
                request_id=request.id,
                total_cents=total_cents,
                valid_until=Quote.validity_date(valid_days),
                gst_included=gst_included,
                note=note,
                version=next_version,
            )
            previous.supersede()
        except ValueError as exc:
            raise InvalidState(str(exc)) from exc
        self._quotes.add(quote)
        return quote

    def refuse(self, actor: Account, request_id: str, reason: str = "") -> QuoteRequest:
        """Decline to quote."""
        request = self._request_for_designer(actor, request_id)
        try:
            request.refuse(reason)
        except ValueError as exc:
            raise InvalidState(str(exc)) from exc
        return request

    # --- reading ----------------------------------------------------------

    def list_for_customer(
        self, actor: Account, state: QuoteRequestState | None = None
    ) -> list[QuoteRequest]:
        """Return the caller's requests, newest first."""
        self._require_customer(actor)
        return self._sorted(self._requests.list_by_customer(actor.id), state)

    def list_for_designer(
        self, actor: Account, state: QuoteRequestState | None = None
    ) -> list[QuoteRequest]:
        """Return the requests sent to the caller's company, newest first."""
        company = self._company_of(actor)
        return self._sorted(self._requests.list_by_company(company.id), state)

    def get_request(self, actor: Account, request_id: str) -> QuoteRequest:
        """Return one request to a party that may see it."""
        request = self._requests.get(request_id)
        if request is None:
            raise QuoteRequestNotFound()
        if not self._may_read(actor, request):
            raise NotPermitted("You may not read this request")
        self._refresh(request)
        return request

    def quotes_for(self, actor: Account, request_id: str) -> list[Quote]:
        """Return every version of a request's quote."""
        request = self.get_request(actor, request_id)
        return self._quotes.list_by_request(request.id)

    # --- helpers ----------------------------------------------------------

    def _sorted(
        self, requests: list[QuoteRequest], state: QuoteRequestState | None
    ) -> list[QuoteRequest]:
        for request in requests:
            self._refresh(request)
        if state is not None:
            requests = [entry for entry in requests if entry.state is state]
        return sorted(requests, key=lambda entry: entry.created_at, reverse=True)

    def _refresh(self, request: QuoteRequest) -> None:
        """Close what time has closed. Called on every read."""
        if request.state is QuoteRequestState.ANSWERED:
            quote = self._quotes.latest_for_request(request.id)
            if quote is not None and quote.state is QuoteState.OFFERED and quote.is_expired():
                quote.expire()
                request.expire()
                return
        if request.is_overdue():
            request.expire()

    def _may_read(self, actor: Account, request: QuoteRequest) -> bool:
        if actor.role in PRIVILEGED_ROLES:
            return True
        if actor.role is Role.CUSTOMER:
            return request.customer_id == actor.id
        company = self._companies.get_by_owner(actor.id)
        return company is not None and company.id == request.company_id

    def _owned_request(self, actor: Account, request_id: str) -> QuoteRequest:
        self._require_customer(actor)
        request = self._requests.get(request_id)
        if request is None:
            raise QuoteRequestNotFound()
        if request.customer_id != actor.id:
            raise NotPermitted("This request belongs to another customer")
        return request

    def _owned_quote(self, actor: Account, quote_id: str) -> tuple[Quote, QuoteRequest]:
        quote = self._quotes.get(quote_id)
        if quote is None:
            raise QuoteNotFound()
        request = self._owned_request(actor, quote.request_id)
        return quote, request

    def _request_for_designer(self, actor: Account, request_id: str) -> QuoteRequest:
        if actor.role is not Role.DESIGNER:
            raise NotPermitted("Only a designer may answer a request")
        company = self._company_of(actor)
        request = self._requests.get(request_id)
        if request is None:
            raise QuoteRequestNotFound()
        if request.company_id != company.id:
            raise NotPermitted("This request went to another company")
        return request

    def _company_of(self, actor: Account):
        if actor.role is not Role.DESIGNER:
            raise NotPermitted("Only a designer has a company")
        company = self._companies.get_by_owner(actor.id)
        if company is None:
            raise CompanyNotFound()
        return company

    @staticmethod
    def _require_customer(actor: Account) -> None:
        if actor.role is not Role.CUSTOMER:
            raise NotPermitted("Only a customer may request a quote")