"""In memory storage for accounts, keyed by id and by email."""

from __future__ import annotations

import threading

from app.domain.account import Account


class AccountRepository:
    """Keeps every account in process memory.

    Two dictionaries are maintained: one keyed by account id for direct
    lookup, one keyed by email for the unique address constraint. There is
    no database in this project, so the repository is the whole store.
    """

    def __init__(self) -> None:
        self._by_id: dict[str, Account] = {}
        self._ids_by_email: dict[str, str] = {}
        self._lock = threading.Lock()

    def add(self, account: Account) -> bool:
        """Store ``account`` unless its email is already taken.

        FastAPI runs sync handlers in a thread pool, so the check and the
        insert must happen under one lock. Returns whether the account was
        stored.
        """
        with self._lock:
            if account.email in self._ids_by_email:
                return False
            self._by_id[account.id] = account
            self._ids_by_email[account.email] = account.id
            return True

    def get(self, account_id: str) -> Account | None:
        """Return the account with ``account_id``, or ``None``."""
        return self._by_id.get(account_id)

    def get_by_email(self, email: str) -> Account | None:
        """Return the account registered under ``email``, or ``None``."""
        account_id = self._ids_by_email.get(email.strip().lower())
        if account_id is None:
            return None
        return self._by_id.get(account_id)

    def list_all(self) -> list[Account]:
        """Return every stored account."""
        return list(self._by_id.values())

    def count(self) -> int:
        """Return how many accounts are stored."""
        return len(self._by_id)

    def clear(self) -> None:
        """Remove every stored account."""
        self._by_id.clear()
        self._ids_by_email.clear()