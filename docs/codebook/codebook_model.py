"""One place that decides which source lines belong to each entry.

Both the document builder and the screenshot renderer import this module, so a
snippet in the PDF and the picture of that snippet always show the same lines.

    from codebook_model import entries
"""

from __future__ import annotations

import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
DATA = json.loads((HERE / "codebook.json").read_text(encoding="utf-8"))

ENTITY_ORDER = [
    "project.py",
    "quote.py",
    "quote_request.py",
    "company.py",
    "account.py",
    "category.py",
    "shortlist.py",
    "catalogue.py",
    "money.py",
    "enums.py",
    "errors.py",
    "passwords.py",
]

PAGE_ORDER = [
    "App",
    "AuthProvider",
    "ProtectedRoute",
    "Home",
    "Login",
    "Register",
    "Dashboard",
    "Search",
    "ProjectDetail",
    "Saved",
    "Designers",
    "DesignerDetail",
    "RequestQuote",
    "Quotes",
    "QuoteDetail",
    "MyProjects",
    "ProjectEditor",
    "Profile",
    "Admin",
    "Platform",
    "BudgetSlider",
]

SOURCE_CACHE: dict[str, list[str]] = {}


def source_of(relative: str) -> list[str]:
    if relative not in SOURCE_CACHE:
        SOURCE_CACHE[relative] = (ROOT / relative).read_text(encoding="utf-8").splitlines()
    return SOURCE_CACHE[relative]


def entity_items() -> list[dict]:
    items = [row for row in DATA["backend"] if "/domain/" in row["file"] and row["kind"] == "class"]
    items.sort(
        key=lambda row: (
            ENTITY_ORDER.index(row["file"].split("/")[-1])
            if row["file"].split("/")[-1] in ENTITY_ORDER
            else 99,
            row["line"],
        )
    )
    return items


def layer_items(folder: str) -> list[dict]:
    items = [row for row in DATA["backend"] if f"/{folder}/" in row["file"]]
    items.sort(key=lambda row: (row["file"], row["line"]))
    return items


def page_items() -> list[dict]:
    pages = [row for row in DATA["frontend"] if row["kind"] == "component"]
    pages.sort(key=lambda row: PAGE_ORDER.index(row["name"]) if row["name"] in PAGE_ORDER else 99)
    return pages


def snippet_key(kind: str, item: dict) -> str:
    return f"{kind}-{item['name']}-{item.get('line', 0)}"


def class_excerpt(item: dict, limit: int = 46) -> list[str]:
    lines = source_of(item["file"])
    start, end = item["lines"]
    block = lines[start - 1 : end]
    if len(block) <= limit:
        return block

    out: list[str] = [f"# {item['file']} — lines {start}–{end}, signatures only"]
    out.extend(item.get("decorators", []))
    bases = f"({', '.join(item['bases'])})" if item["bases"] else ""
    out.append(f"class {item['name']}{bases}:")
    if item["doc"]:
        out.append(f'    """{item["doc"]}"""')
    for field in item.get("fields", []):
        text = f"    {field['name']}: {field['type']}"
        if field["default"]:
            text += f" = {field['default']}"
        out.append(text)
    if item.get("fields"):
        out.append("")
    for method in item.get("methods", []):
        for name in method.get("decorators", []):
            out.append(f"    {name}")
        out.append(f"    {method['signature']}")
        if method.get("doc"):
            out.append(f'        """{method["doc"]}"""')
    return out


def function_excerpt(item: dict, limit: int = 26) -> list[str]:
    lines = source_of(item["file"])
    start, end = item["lines"]
    block = lines[start - 1 : end]
    if len(block) <= limit:
        return block
    out = [f"# {item['file']} — lines {start}–{end}, first 20 lines of {len(block)}"]
    out.extend(block[:20])
    out.append("    ...")
    return out


def page_excerpt(item: dict, limit: int = 28) -> list[str]:
    lines = source_of(item["file"])
    start = item["line"]
    return lines[start - 1 : start + min(limit, len(lines) - start + 1)]


def lang_for(relative: str) -> str:
    return "python" if relative.endswith(".py") else "tsx"


def entries() -> list[dict]:
    """Every snippet the document shows, in document order."""
    rows: list[dict] = []

    for item in entity_items():
        rows.append(
            {
                "key": snippet_key("entity", item),
                "kind": "entity",
                "name": item["name"],
                "file": item["file"],
                "start": item["lines"][0],
                "end": item["lines"][1],
                "lang": "python",
                "code": class_excerpt(item),
            }
        )

    for folder, limit in (("repositories", 40), ("services", 40), ("api", 30)):
        for item in layer_items(folder):
            block = (
                class_excerpt(item)
                if item["kind"] == "class"
                else function_excerpt(item, limit=limit)
            )
            rows.append(
                {
                    "key": snippet_key(folder, item),
                    "kind": folder,
                    "name": item["name"],
                    "file": item["file"],
                    "start": item["lines"][0],
                    "end": item["lines"][1],
                    "lang": "python",
                    "code": block,
                }
            )

    for item in page_items():
        rows.append(
            {
                "key": snippet_key("page", item),
                "kind": "page",
                "name": item["name"],
                "file": item["file"],
                "start": item["line"],
                "end": item["line"],
                "lang": "tsx",
                "code": page_excerpt(item),
            }
        )
    return rows


if __name__ == "__main__":
    rows = entries()
    print(len(rows), "snippets")
    by_kind: dict[str, int] = {}
    for row in rows:
        by_kind[row["kind"]] = by_kind.get(row["kind"], 0) + 1
    print(by_kind)
