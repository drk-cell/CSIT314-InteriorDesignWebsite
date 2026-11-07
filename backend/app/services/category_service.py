"""Category use cases: staff curate the room list, everyone reads it."""

from __future__ import annotations

from app.domain.account import Account
from app.domain.category import Category
from app.domain.enums import PRIVILEGED_ROLES
from app.domain.errors import NotPermitted
from app.repositories.category_repository import CategoryRepository


class CategoryNotFound(Exception):
    """No category matches the supplied id."""

    def __init__(self) -> None:
        super().__init__("Category not found")


class CategoryExists(Exception):
    """A category with that label already exists."""

    def __init__(self) -> None:
        super().__init__("A category with that name already exists")


class CategoryService:
    """Applies the staff rules on top of the category store."""

    def __init__(self, categories: CategoryRepository) -> None:
        self._categories = categories

    def list_active(self) -> list[Category]:
        """Return the labels a dropdown should show."""
        return self._categories.list_active()

    def list_all(self, actor: Account) -> list[Category]:
        """Return every category, archived ones included."""
        self._require_staff(actor)
        return self._categories.list_all()

    def add(self, actor: Account, name: str) -> Category:
        """Create a category."""
        self._require_staff(actor)
        try:
            category = Category(name=name)
        except ValueError as exc:
            raise ValueError(str(exc)) from exc
        if not self._categories.add(category):
            raise CategoryExists()
        return category

    def rename(self, actor: Account, category_id: str, name: str) -> Category:
        """Change a category label."""
        self._require_staff(actor)
        category = self._categories.get(category_id)
        if category is None:
            raise CategoryNotFound()
        clash = self._categories.find_by_name(name)
        if clash is not None and clash.id != category.id:
            raise CategoryExists()
        category.rename(name)
        return category

    def get(self, actor: Account, category_id: str) -> Category:
        """Return one category for staff."""
        self._require_staff(actor)
        category = self._categories.get(category_id)
        if category is None:
            raise CategoryNotFound()
        return category

    def set_active(self, actor: Account, category_id: str, active: bool) -> Category:
        """Archive or restore a category."""
        self._require_staff(actor)
        category = self._categories.get(category_id)
        if category is None:
            raise CategoryNotFound()
        if active:
            category.restore()
        else:
            category.archive()
        return category

    @staticmethod
    def _require_staff(actor: Account) -> None:
        if actor.role not in PRIVILEGED_ROLES:
            raise NotPermitted("Only platform staff may manage categories")