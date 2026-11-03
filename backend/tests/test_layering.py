"""The domain layer must not depend on the layers above it.

This is the structural rule behind b-c-e. If an entity imports the web
framework, the token module or the repository, the layering claim in the report
stops being true, so the rule is checked as a test.
"""

from __future__ import annotations

import ast
from pathlib import Path

DOMAIN = Path(__file__).resolve().parents[1] / "app" / "domain"

OUTER_LAYERS = ("app.api", "app.services", "app.repositories", "app.security", "app.config")
THIRD_PARTY = ("fastapi", "starlette", "jwt", "pydantic", "sqlalchemy")


def imported_modules(path: Path) -> list[tuple[int, str]]:
    """Return every ``(line, module)`` an import statement names in ``path``."""
    tree = ast.parse(path.read_text(encoding="utf-8"))
    found: list[tuple[int, str]] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            found.extend((node.lineno, alias.name) for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module is not None:
            found.append((node.lineno, node.module))
    return found


def test_domain_imports_nothing_from_the_outer_layers() -> None:
    offenders: list[str] = []

    for path in sorted(DOMAIN.glob("*.py")):
        for line, module in imported_modules(path):
            root = module.split(".")[0]
            if module.startswith(OUTER_LAYERS) or root in THIRD_PARTY:
                offenders.append(f"{path.name}:{line} imports {module}")

    assert offenders == [], "domain layer reached outward:\n" + "\n".join(offenders)


def test_password_hashing_is_reachable_without_the_token_module() -> None:
    from app.domain.passwords import hash_password, verify_password

    stored = hash_password("secret123")

    assert verify_password("secret123", stored) is True
    assert verify_password("wrong", stored) is False