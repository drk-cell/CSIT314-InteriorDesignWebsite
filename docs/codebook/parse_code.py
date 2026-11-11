"""Read the source tree and describe every class and function.

The output is one JSON file, ``codebook.json``, that ``build_codebook.py`` turns
into the document. Nothing here imports the application: the files are parsed as
text, so the inventory also works on a machine without the virtual environment.

    python docs/codebook/parse_code.py
"""

from __future__ import annotations

import ast
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BACKEND = ROOT / "backend" / "app"
FRONTEND = ROOT / "frontend" / "src"

# Folder name -> the BCE role that folder plays in the diagrams.
LAYERS = {
    "domain": ("Entity", "Business objects and their rules"),
    "repositories": ("Entity (access)", "Stores and finds entity objects"),
    "services": ("Control", "Use case logic that coordinates entities"),
    "api": ("Control (boundary)", "HTTP entry points; validation and permission checks"),
    "schemas": ("Data transfer", "Shapes sent to and from the browser"),
}


def unparse(node: ast.AST | None) -> str:
    if node is None:
        return ""
    try:
        return ast.unparse(node)
    except Exception:  # noqa: BLE001 - unparse is best effort on old syntax
        return ""


def signature(node: ast.FunctionDef | ast.AsyncFunctionDef) -> str:
    parts = []
    args = node.args
    positional = args.posonlyargs + args.args
    defaults = [None] * (len(positional) - len(args.defaults)) + list(args.defaults)
    for index, (arg, default) in enumerate(zip(positional, defaults)):
        if index == 0 and arg.arg in {"self", "cls"}:
            continue
        text = arg.arg
        if arg.annotation is not None:
            text += f": {unparse(arg.annotation)}"
        if default is not None:
            text += f" = {unparse(default)}"
        parts.append(text)
    if args.vararg:
        parts.append("*" + args.vararg.arg)
    if args.kwarg:
        parts.append("**" + args.kwarg.arg)
    prefix = "async def" if isinstance(node, ast.AsyncFunctionDef) else "def"
    result = f"{prefix} {node.name}({', '.join(parts)})"
    if node.returns is not None:
        result += f" -> {unparse(node.returns)}"
    return result


def first_line(node: ast.AST) -> str:
    doc = ast.get_docstring(node) or ""
    return doc.strip().splitlines()[0].strip() if doc.strip() else ""


def decorators(node: ast.AST) -> list[str]:
    """Return the decorators as they were written, arguments included."""
    return ["@" + unparse(item) for item in getattr(node, "decorator_list", [])]


def describe_class(node: ast.ClassDef, path: Path, layer: str) -> dict:
    fields = []
    methods = []
    for child in node.body:
        if isinstance(child, ast.AnnAssign) and isinstance(child.target, ast.Name):
            fields.append(
                {
                    "name": child.target.id,
                    "type": unparse(child.annotation),
                    "default": unparse(child.value),
                }
            )
        elif isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
            methods.append(
                {
                    "name": child.name,
                    "signature": signature(child),
                    "doc": first_line(child),
                    "decorators": decorators(child),
                    "lines": [child.lineno, getattr(child, "end_lineno", child.lineno)],
                }
            )
    return {
        "kind": "class",
        "name": node.name,
        "bases": [unparse(base) for base in node.bases],
        "doc": first_line(node),
        "decorators": decorators(node),
        "file": str(path.relative_to(ROOT)).replace("\\", "/"),
        "line": node.lineno,
        "lines": [node.lineno, getattr(node, "end_lineno", node.lineno)],
        "layer": layer,
        "fields": fields,
        "methods": methods,
        "public_methods": [m["name"] for m in methods if not m["name"].startswith("_")],
    }


def describe_function(node, path: Path, layer: str) -> dict:
    return {
        "kind": "function",
        "name": node.name,
        "signature": signature(node),
        "doc": first_line(node),
        "decorators": decorators(node),
        "file": str(path.relative_to(ROOT)).replace("\\", "/"),
        "line": node.lineno,
        "layer": layer,
        "lines": [node.lineno, getattr(node, "end_lineno", node.lineno)],
    }


def parse_backend() -> list[dict]:
    items: list[dict] = []
    for path in sorted(BACKEND.rglob("*.py")):
        if path.name == "__init__.py":
            continue
        layer = LAYERS.get(path.parent.name, ("Support", ""))[0]
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in tree.body:
            if isinstance(node, ast.ClassDef):
                items.append(describe_class(node, path, layer))
            elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                items.append(describe_function(node, path, layer))
    return items


EXPORT_RE = re.compile(
    r"export\s+(?:default\s+)?(?:async\s+)?function\s+(\w+)\s*\(([^)]*)\)", re.S
)
COMPONENT_RE = re.compile(r"export\s+(?:default\s+)?function\s+([A-Z]\w*)\s*\(")

ROUTE_RE = re.compile(r'<Route\s+path="([^"]+)"\s+element=\{<(\w+)')


def parse_routes(text: str) -> list[dict]:
    """Routes are written over several lines, with a ProtectedRoute in between."""
    lines = text.splitlines()
    routes: list[dict] = []
    for index, line in enumerate(lines):
        if not re.search(r"<Route(\s|>|$)", line):
            continue
        window = [line]
        if not line.strip().endswith("/>"):
            for row in lines[index + 1 : index + 12]:
                if re.search(r"<Route(\s|>|$)", row):
                    break
                window.append(row)
                if "</Route>" in row or row.strip().endswith("/>"):
                    break
        path = component = roles = None
        for row in window:
            if path is None:
                match = re.search(r'path="([^"]+)"', row)
                if match:
                    path = match.group(1)
            if roles is None:
                match = re.search(r"roles=\{\[([^\]]*)\]\}", row)
                if match:
                    roles = ", ".join(
                        part.strip().strip("'\"") for part in match.group(1).split(",") if part.strip()
                    )
            for match in re.finditer(r"<([A-Z]\w+)\s*/>", row):
                name = match.group(1)
                if name not in {"ProtectedRoute", "Navigate"}:
                    component = name
                    break
            if path and component:
                break
        if path:
            guarded = any("ProtectedRoute" in row for row in window)
            routes.append(
                {
                    "path": path,
                    "component": component or "redirect",
                    "roles": roles or ("signed in" if guarded else "any"),
                }
            )
    return routes


def layer_for(relative: str) -> str:
    name = relative.rsplit("/", 1)[-1]
    if name == "api.ts":
        return "Boundary (API client)"
    if name == "auth.tsx":
        return "Control (session)"
    if name == "types.ts":
        return "Data transfer"
    if name == "App.tsx":
        return "Boundary (routing)"
    if "/pages/" in relative:
        return "Boundary (page)"
    if "/components/" in relative:
        return "Boundary (component)"
    return "Boundary"


def parse_frontend() -> list[dict]:
    items: list[dict] = []
    for path in sorted(list(FRONTEND.rglob("*.tsx")) + list(FRONTEND.rglob("*.ts"))):
        text = path.read_text(encoding="utf-8")
        relative = str(path.relative_to(ROOT)).replace("\\", "/")
        import_block = re.search(r"import\s*\{([^}]*)\}\s*from\s*'\.\.?/api'", text, re.S)
        calls: list[str] = []
        if import_block:
            calls = sorted(
                {
                    name.strip().split(" as ")[0].strip()
                    for name in import_block.group(1).split(",")
                    if name.strip()
                }
            )
        for match in COMPONENT_RE.finditer(text):
            start = match.start()
            line = text.count("\n", 0, start) + 1
            body_call = text[start : start + 400]
            items.append(
                {
                    "kind": "component",
                    "name": match.group(1),
                    "file": relative,
                    "line": line,
                    "api": calls,
                    "hooks": sorted(
                        set(re.findall(r"use(State|Effect|Params|Navigate|Context|Ref)", text))
                    ),
                    "doc": "",
                    "layer": layer_for(relative),
                    "imports_api": bool(calls),
                }
            )
        for match in EXPORT_RE.finditer(text):
            name = match.group(1)
            if name[0].isupper() and name in {i["name"] for i in items if i["file"] == relative}:
                continue
            line = text.count("\n", 0, match.start()) + 1
            items.append(
                {
                    "kind": "function",
                    "name": name,
                    "signature": f"function {name}({match.group(2).strip()})",
                    "file": relative,
                    "line": line,
                    "doc": "",
                    "layer": layer_for(relative),
                }
            )
    return items


def main() -> int:
    app_tsx = (FRONTEND / "App.tsx").read_text(encoding="utf-8")
    routes = parse_routes(app_tsx)

    data = {
        "backend": parse_backend(),
        "frontend": parse_frontend(),
        "routes": routes,
        "counts": {},
    }
    for key in ("backend", "frontend"):
        rows = data[key]
        data["counts"][key] = {
            "classes": sum(1 for row in rows if row["kind"] == "class"),
            "functions": sum(1 for row in rows if row["kind"] == "function"),
            "components": sum(1 for row in rows if row["kind"] == "component"),
            "items": len(rows),
        }
    out = Path(__file__).resolve().parent / "codebook.json"
    out.write_text(json.dumps(data, indent=1), encoding="utf-8")
    print(json.dumps(data["counts"], indent=1))
    print("wrote", out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
