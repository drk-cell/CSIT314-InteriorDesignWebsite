"""Company use cases: create, read and update the designer profile."""

from __future__ import annotations

from app.domain.account import Account
from app.domain.company import Company
from app.domain.enums import Role
from app.domain.errors import CompanyAlreadyExists, CompanyNotFound, NotPermitted
from app.repositories.company_repository import CompanyRepository


class CompanyService:
    """Applies the company profile rules on top of the repository."""

    def __init__(self, companies: CompanyRepository) -> None:
        self._companies = companies

    def create(
        self,
        actor: Account,
        name: str,
        description: str,
        contact_email: str,
        contact_phone: str,
        location: str,
        logo_url: str = "",
    ) -> Company:
        """Create the company profile for ``actor``.

        One profile per designer. Only an interior designer may hold one.
        """
        self._require_designer(actor)
        company = Company(
            owner_id=actor.id,
            name=name,
            description=description,
            contact_email=contact_email,
            contact_phone=contact_phone,
            location=location,
            logo_url=logo_url,
        )
        if not self._companies.add(company):
            raise CompanyAlreadyExists()
        return company

    def get_for_owner(self, actor: Account) -> Company:
        """Return the profile owned by ``actor``."""
        self._require_designer(actor)
        company = self._companies.get_by_owner(actor.id)
        if company is None:
            raise CompanyNotFound()
        return company

    def update(
        self,
        actor: Account,
        *,
        name: str | None = None,
        description: str | None = None,
        contact_email: str | None = None,
        contact_phone: str | None = None,
        location: str | None = None,
        logo_url: str | None = None,
    ) -> Company:
        """Change only the fields that were supplied.

        The entity validates each change, so a blank name or a bad address
        raises ``ValueError`` before the record is touched.
        """
        company = self.get_for_owner(actor)
        if name is not None:
            company.rename(name)
        if description is not None:
            company.update_description(description)
        if contact_email is not None or contact_phone is not None:
            company.update_contact(
                contact_email if contact_email is not None else company.contact_email,
                contact_phone if contact_phone is not None else company.contact_phone,
            )
        if location is not None:
            company.set_location(location)
        if logo_url is not None:
            company.attach_logo(logo_url)
        return company

    def get(self, company_id: str) -> Company:
        """Return a company by id. Any signed in account may read it."""
        company = self._companies.get(company_id)
        if company is None:
            raise CompanyNotFound()
        return company

    def list_companies(self) -> list[Company]:
        """Return every company, sorted by name for a stable listing."""
        return sorted(self._companies.list_all(), key=lambda company: company.name.lower())

    @staticmethod
    def _require_designer(actor: Account) -> None:
        if actor.role is not Role.DESIGNER:
            raise NotPermitted("Only an interior designer may manage a company profile")