"""Write the code documentation from ``codebook.json``.

One entry per class and one per function. Every entry gives the file path and
the line range, because the class diagram and the sequence diagrams in the report
have to point back at the code.

    python docs/codebook/build_codebook.py
"""

from __future__ import annotations

import json
import re
import subprocess
from datetime import date
from pathlib import Path

from docx import Document
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_BREAK
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Mm, Pt, RGBColor

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
DATA = json.loads((HERE / "codebook.json").read_text(encoding="utf-8"))
OUT = HERE / "CSIT314-Code-Documentation.docx"

INK = RGBColor(0x11, 0x18, 0x27)
MUTED = RGBColor(0x6B, 0x72, 0x80)
ACCENT = RGBColor(0x1F, 0x5C, 0x4A)
CODE_BG = "F2F4F7"

SOURCE_CACHE: dict[str, list[str]] = {}


def source_of(relative: str) -> list[str]:
    if relative not in SOURCE_CACHE:
        SOURCE_CACHE[relative] = (ROOT / relative).read_text(encoding="utf-8").splitlines()
    return SOURCE_CACHE[relative]


# --------------------------------------------------------------------- docx parts
def heading(doc, text: str, level: int) -> None:
    paragraph = doc.add_heading(text, level=level)
    for run in paragraph.runs:
        run.font.name = "Calibri"
        run.font.color.rgb = INK if level == 1 else ACCENT


def body(doc, text: str, size: float = 10, bold_lead: str | None = None) -> None:
    paragraph = doc.add_paragraph()
    paragraph.paragraph_format.space_after = Pt(4)
    if bold_lead:
        lead = paragraph.add_run(bold_lead)
        lead.bold = True
        lead.font.size = Pt(size)
    run = paragraph.add_run(text)
    run.font.size = Pt(size)


def shade(paragraph, hex_fill: str) -> None:
    shd = OxmlElement("w:shd")
    shd.set(qn("w:fill"), hex_fill)
    paragraph._p.get_or_add_pPr().append(shd)


def code(doc, lines: list[str], caption: str) -> None:
    """A code block: one paragraph per line, monospace, thin grey background."""
    label = doc.add_paragraph()
    label.paragraph_format.space_before = Pt(4)
    label.paragraph_format.space_after = Pt(1)
    run = label.add_run(caption)
    run.font.name = "Consolas"
    run.font.size = Pt(7.5)
    run.font.color.rgb = MUTED
    run.bold = True

    if not lines:
        lines = ["(no lines)"]
    for index, text in enumerate(lines):
        paragraph = doc.add_paragraph()
        paragraph.paragraph_format.space_after = Pt(0)
        paragraph.paragraph_format.space_before = Pt(0)
        paragraph.paragraph_format.left_indent = Mm(2)
        paragraph.paragraph_format.keep_together = True
        if index < len(lines) - 1:
            paragraph.paragraph_format.keep_with_next = True
        shade(paragraph, CODE_BG)
        run = paragraph.add_run(text.replace("\t", "    ") if text else " ")
        run.font.name = "Consolas"
        run.font.size = Pt(7.5)
        run.font.color.rgb = INK
    doc.add_paragraph().paragraph_format.space_after = Pt(2)


def table(doc, header: list[str], rows: list[list[str]], widths: list[int], size: float = 8.5):
    grid = doc.add_table(rows=1, cols=len(header))
    grid.style = "Table Grid"
    grid.alignment = WD_TABLE_ALIGNMENT.CENTER
    grid.autofit = False
    for index, text in enumerate(header):
        cell = grid.rows[0].cells[index]
        cell.text = ""
        run = cell.paragraphs[0].add_run(text)
        run.bold = True
        run.font.size = Pt(size)
        shd = OxmlElement("w:shd")
        shd.set(qn("w:fill"), "EAF1ED")
        cell._tc.get_or_add_tcPr().append(shd)
    for row in rows:
        cells = grid.add_row().cells
        for index, text in enumerate(row):
            cells[index].text = ""
            run = cells[index].paragraphs[0].add_run(text)
            run.font.size = Pt(size)
            run.font.name = "Consolas" if index == 0 and len(header) > 2 else "Calibri"
    for row in grid.rows:
        for index, width in enumerate(widths):
            row.cells[index].width = Mm(width)
    doc.add_paragraph().paragraph_format.space_after = Pt(2)


def page_break(doc) -> None:
    doc.add_paragraph().add_run().add_break(WD_BREAK.PAGE)


def line_label(item: dict) -> str:
    start, end = item.get("lines", [item.get("line", 0), item.get("line", 0)])
    return f"{item['file']}  ·  lines {start}–{end}"


def short_label(item: dict) -> str:
    start, end = item.get("lines", [item.get("line", 0), item.get("line", 0)])
    return f"lines {start}–{end}"


# ------------------------------------------------------------------- code excerpts
def class_excerpt(item: dict, limit: int = 46) -> list[str]:
    lines = source_of(item["file"])
    start, end = item["lines"]
    block = lines[start - 1 : end]
    if len(block) <= limit:
        return block

    out: list[str] = [f"# {item['file']} — lines {start}–{end}, signatures only"]
    out.extend(f"@{name.lstrip('@')}" for name in item.get("decorators", []))
    bases = f"({', '.join(item['bases'])})" if item["bases"] else ""
    out.append(f"class {item['name']}{bases}:")
    if item["doc"]:
        out.append(f'    """{item["doc"]}"""')
    for field in item.get("fields", []):
        text = f"    {field['name']}: {field['type']}"
        if field["default"]:
            text += f" = {field['default'][:40]}"
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


# ------------------------------------------------------------------- typed helpers
ENTITY_ENDPOINT = re.compile(r"@router\.(get|post|put|patch|delete)\(\s*\"([^\"]*)\"")


def endpoint_of(item: dict) -> str:
    for name in item.get("decorators", []):
        match = re.search(r"@router\.(\w+)", name)
        if match:
            return match.group(1).upper()
    return ""


def route_path_of(item: dict) -> str:
    lines = source_of(item["file"])
    for index in range(item["line"] - 1, max(item["line"] - 6, -1), -1):
        match = ENTITY_ENDPOINT.search(lines[index])
        if match:
            return match.group(2) or "/"
    return ""


def git_sha() -> str:
    try:
        return subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
        ).stdout.strip()
    except Exception:  # noqa: BLE001
        return "unknown"


# ------------------------------------------------------------------------- sections
def cover(doc) -> None:
    doc.add_paragraph().paragraph_format.space_before = Pt(80)
    title = doc.add_paragraph()
    run = title.add_run("Code Documentation")
    run.bold = True
    run.font.size = Pt(32)
    run.font.color.rgb = INK

    subtitle = doc.add_paragraph()
    sub = subtitle.add_run("Classes, functions and the BCE model")
    sub.font.size = Pt(15)
    sub.font.color.rgb = ACCENT

    body(doc, "Every class and every function in the back end, and every component in the front end.", 10.5)
    body(
        doc,
        "Each entry names the file and the line range, so a class diagram box or a "
        "sequence-diagram lifeline can point at the exact code.",
        10,
    )
    counts = DATA["counts"]
    body(
        doc,
        f"{counts['backend']['classes']} classes and {counts['backend']['functions']} module functions "
        f"in the back end; {counts['frontend']['components']} components and "
        f"{counts['frontend']['functions']} exported functions in the front end.",
        10,
    )
    body(doc, f"Repository CSIT314-InteriorDesignWebsite · commit {git_sha()} · {date.today():%d %B %Y}", 9)
    page_break(doc)

    # contents
    title = doc.add_paragraph()
    run = title.add_run("Contents")
    run.bold = True
    run.font.size = Pt(18)
    run.font.color.rgb = INK
    paragraph = doc.add_paragraph()
    field_begin = OxmlElement("w:fldChar")
    field_begin.set(qn("w:fldCharType"), "begin")
    instr = OxmlElement("w:instrText")
    instr.set(qn("xml:space"), "preserve")
    instr.text = 'TOC \\o "1-2" \\h \\z \\u'
    field_end = OxmlElement("w:fldChar")
    field_end.set(qn("w:fldCharType"), "end")
    run = paragraph.add_run()
    run._r.append(field_begin)
    run._r.append(instr)
    run._r.append(field_end)
    page_break(doc)


def introduction(doc) -> None:
    heading(doc, "1  How to read this document", 1)
    body(
        doc,
        "The platform is described in the Boundary-Control-Entity form. A class diagram "
        "draws every class below as a box. A sequence diagram draws the functions below as "
        "messages between lifelines. This document is the link between the two.",
    )
    body(
        doc,
        "Each entry has the same parts: the name, the file and line range, the role, the "
        "purpose taken from the docstring, a table of attributes and methods, and a code "
        "excerpt. A long class shows its signatures; a short one shows the whole class.",
    )

    heading(doc, "1.1  The five roles", 2)
    table(
        doc,
        ["Role", "Folder", "What it does", "Diagram form"],
        [
            ["Boundary", "frontend/src/pages, components", "Draws a screen, collects input, calls the API client", "Lifeline on the left"],
            ["Boundary (API client)", "frontend/src/api.ts", "One typed function per endpoint", "Message to the server"],
            ["Control", "backend/app/api, backend/app/services", "Checks permission, runs the use case, returns a shape", "Lifeline in the middle"],
            ["Entity", "backend/app/domain", "Holds the data and the rules that protect it", "Class box"],
            ["Entity (access)", "backend/app/repositories", "Finds and stores entity objects", "Lifeline beside the entity"],
            ["Data transfer", "backend/app/schemas, frontend/src/types.ts", "Shapes that cross the HTTP edge", "Not drawn; shown as parameters"],
        ],
        [34, 42, 62, 34],
    )

    heading(doc, "1.2  Where each layer lives", 2)
    rows = []
    for folder, (role, _) in {
        "domain": ("Entity", ""),
        "repositories": ("Entity (access)", ""),
        "services": ("Control", ""),
        "api": ("Control (boundary)", ""),
        "schemas": ("Data transfer", ""),
    }.items():
        items = [row for row in DATA["backend"] if f"/{folder}/" in row["file"]]
        classes = [row for row in items if row["kind"] == "class"]
        functions = [row for row in items if row["kind"] == "function"]
        files = len({row["file"] for row in items})
        rows.append([role, f"backend/app/{folder}", str(files), str(len(classes)), str(len(functions))])
    table(doc, ["Role", "Folder", "Files", "Classes", "Functions"], rows, [40, 60, 20, 22, 26])

    heading(doc, "1.3  The routers, and the paths they serve", 2)
    routers = [row for row in DATA["backend"] if row["kind"] == "function" and endpoint_of(row)]
    body(
        doc,
        f"The back end exposes {len(routers)} HTTP operations. Each one is a control function; "
        "the table gives the verb, the path and the code position.",
        10,
    )
    rows = []
    for row in routers:
        rows.append(
            [
                endpoint_of(row),
                route_path_of(row),
                f"{row['name']}()",
                f"{row['file'].split('/')[-1]}:{row['line']}",
            ]
        )
    table(doc, ["Verb", "Path", "Function", "Where"], rows, [16, 46, 52, 46], size=7.5)


def entity_section(doc) -> None:
    page_break(doc)
    heading(doc, "2  Entity layer: backend/app/domain", 1)
    body(
        doc,
        "These classes own the data. Each one guards its own rules in the constructor or in "
        "its methods, so a caller cannot create an object in a state the business forbids. "
        "This is the set of boxes for the class diagram.",
    )

    order = ["project.py", "quote.py", "quote_request.py", "company.py", "account.py", "category.py", "shortlist.py", "catalogue.py", "money.py", "enums.py", "errors.py", "passwords.py"]
    items = [row for row in DATA["backend"] if "/domain/" in row["file"] and row["kind"] == "class"]
    items.sort(key=lambda row: (order.index(row["file"].split("/")[-1]) if row["file"].split("/")[-1] in order else 99, row["line"]))

    for item in items:
        heading(doc, f"2.{items.index(item) + 1}  {item['name']}", 2)
        body(doc, line_label(item), 8.5)
        if item["bases"]:
            body(doc, "Extends " + ", ".join(item["bases"]) + ".", 9)
        if item["doc"]:
            body(doc, item["doc"], 9.5)
        if item.get("fields"):
            table(
                doc,
                ["Attribute", "Type", "Default"],
                [[f["name"], f["type"], f["default"] or "—"] for f in item["fields"]],
                [46, 70, 50],
                size=8,
            )
        if item.get("methods"):
            rows = []
            for method in item["methods"]:
                start, end = method.get("lines", [0, 0])
                rows.append([method["signature"], method.get("doc", ""), f"{start}–{end}"])
            table(doc, ["Method", "Purpose", "Lines"], rows, [88, 56, 20], size=7.5)
        code(doc, class_excerpt(item), short_label(item))


def layer_section(doc, number: str, title: str, folder: str, intro: str, excerpt_limit: int) -> None:
    page_break(doc)
    heading(doc, f"{number}  {title}", 1)
    body(doc, intro)
    items = [row for row in DATA["backend"] if f"/{folder}/" in row["file"]]
    items.sort(key=lambda row: (row["file"], row["line"]))
    for index, item in enumerate(items, start=1):
        anchor = item["name"] if item["kind"] == "class" else f"{item['name']}()"
        heading(doc, f"{number}.{index}  {anchor}", 2)
        body(doc, line_label(item), 8.5)
        if item.get("decorators") and item["kind"] == "function":
            body(doc, "  ".join(item["decorators"]), 8)
        if item["doc"]:
            body(doc, item["doc"], 9.5)
        if item["kind"] == "class":
            if item.get("methods"):
                rows = []
                for method in item["methods"]:
                    start, end = method.get("lines", [0, 0])
                    rows.append([method["signature"], method.get("doc", ""), f"{start}–{end}"])
                table(doc, ["Method", "Purpose", "Lines"], rows, [88, 56, 20], size=7.5)
            code(doc, class_excerpt(item), short_label(item))
        else:
            code(doc, function_excerpt(item, limit=excerpt_limit), short_label(item))


def schema_section(doc) -> None:
    page_break(doc)
    heading(doc, "6  Data transfer shapes: backend/app/schemas", 1)
    body(
        doc,
        "A schema is not a domain object. It states what the browser may send and what it "
        "receives. The validators in these classes reject a bad request before any use case runs.",
    )
    items = [row for row in DATA["backend"] if "/schemas/" in row["file"] and row["kind"] == "class"]
    items.sort(key=lambda row: (row["file"], row["line"]))
    rows = []
    for item in items:
        start, end = item["lines"]
        fields = ", ".join(f["name"] for f in item.get("fields", []))[:70]
        rows.append([item["name"], item["file"].split("/")[-1], f"{start}–{end}", fields or "—"])
    table(doc, ["Schema", "File", "Lines", "Fields"], rows, [46, 34, 18, 66], size=7.5)

    body(
        doc,
        "The matching front-end types live in frontend/src/types.ts. They mirror these "
        "shapes and add the enum values the browser needs.",
        9.5,
    )
    code(
        doc,
        [f"// frontend/src/types.ts · lines 1–{len(source_of('frontend/src/types.ts'))}",
         "export type Role = 'CUSTOMER' | 'DESIGNER' | 'ADMIN';"]
        + [
            f"export interface {name} {{ ... }}"
            for name in re.findall(r"export interface (\w+)", "\n".join(source_of("frontend/src/types.ts")))
        ],
        "frontend/src/types.ts — the interfaces the API answers with",
    )


def boundary_section(doc) -> None:
    page_break(doc)
    heading(doc, "7  Boundary layer: the browser", 1)
    body(
        doc,
        "Each page is a boundary object. It draws the screen, holds the form state and calls "
        "one function in api.ts per endpoint. The table under each page names the calls it "
        "makes, so a sequence diagram can draw the message from page to API.",
    )

    routes = DATA.get("routes", [])
    if routes:
        table(
            doc,
            ["Route", "Component"],
            [[row["path"], row["component"]] for row in routes],
            [80, 60],
        )

    pages = [row for row in DATA["frontend"] if row["kind"] == "component"]
    order = [
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
    pages.sort(key=lambda row: order.index(row["name"]) if row["name"] in order else 99)
    for index, page in enumerate(pages, start=1):
        heading(doc, f"7.{index}  {page['name']}", 2)
        label = f"{page['file']}  ·  line {page['line']}"
        body(doc, label, 8.5)
        if page.get("api"):
            body(doc, "Calls: " + ", ".join(page["api"]) + ".", 9)
        else:
            body(doc, "Calls: no endpoint directly; it composes other components.", 9)
        hooks = page.get("hooks") or []
        if hooks:
            body(doc, "React hooks: " + ", ".join("use" + hook for hook in hooks) + ".", 9)

        lines = source_of(page["file"])
        # handlers declared inside the page: async functions and handle* names
        handlers = [
            (number, text.strip())
            for number, text in enumerate(lines, start=1)
            if re.match(r"\s*(async\s+)?function\s+\w+\(", text)
        ]
        if handlers:
            table(
                doc,
                ["Function", "Line"],
                [[text[:96], str(number)] for number, text in handlers[:14]],
                [120, 20],
                size=7.5,
            )
        start = page["line"]
        code(
            doc,
            lines[start - 1 : start + min(28, len(lines) - start + 1)],
            f"from line {start} · first 28 lines",
        )

    heading(doc, "7.99  The API client", 2)
    body(doc, "frontend/src/api.ts · one function per endpoint, all of them typed.", 8.5)
    api_functions = [
        row for row in DATA["frontend"] if row["kind"] == "function" and row["file"].endswith("api.ts")
    ]
    table(
        doc,
        ["Client function", "Line"],
        [[row["signature"][:80], str(row["line"])] for row in api_functions],
        [120, 20],
        size=7.5,
    )


def client_line(name: str) -> str:
    for row in DATA["frontend"]:
        if row["kind"] == "function" and row["file"].endswith("api.ts") and row["name"] == name:
            return f"frontend/src/api.ts:{row['line']}"
    return "frontend/src/api.ts"


def sequence_section(doc) -> None:
    heading(doc, "8  Sequence walks", 1)
    body(
        doc,
        "Each walk lists the objects in order: boundary, control, entity access, entity. "
        "Every step names the file and the line, so a drawing can be traced back to the code. "
        "The names below are the names in the source, not summaries.",
    )

    walks = [
        (
            "8.1  A customer searches by photo",
            [
                ("Boundary", "Search.tsx · analysePhoto", "frontend/src/pages/Search.tsx:111", "Reads the chosen file and shows the preview"),
                ("Boundary", "api.ts · suggestTagsFromUpload", client_line("suggestTagsFromUpload"), "POST /api/images/tags with the file"),
                ("Control", "images.py · tags_for_upload", "backend/app/api/images.py:122", "Checks the size and the type, then reads the bytes"),
                ("Control", "tag_suggestion_service.py · suggest_tags", "backend/app/services/tag_suggestion_service.py:55", "Colour palette, object labels, tag list"),
                ("Boundary", "Search.tsx · results", "frontend/src/pages/Search.tsx", "Chips render; searchProjects ranks the catalogue"),
            ],
        ),
        (
            "8.2  A customer requests a quote",
            [
                ("Boundary", "RequestQuote.tsx · submit", "frontend/src/pages/RequestQuote.tsx:31", "Validates the form fields"),
                ("Boundary", "api.ts · submitQuoteRequest", client_line("submitQuoteRequest"), "POST /api/quotes/requests"),
                ("Control", "quotes.py · submit_request", "backend/app/api/quotes.py:63", "Rejects a non-customer, maps errors to codes"),
                ("Control", "quote_service.py · QuoteService.submit", "backend/app/services/quote_service.py:49–88", "Builds the request from the payload"),
                ("Entity (access)", "quote_repository.py · QuoteRequestRepository.add", "backend/app/repositories/quote_repository.py:18–24", "Stores the request"),
            ],
        ),
        (
            "8.3  A designer answers a request",
            [
                ("Boundary", "QuoteDetail.tsx · submitAnswer", "frontend/src/pages/QuoteDetail.tsx:77", "Reads total, validity and the GST choice"),
                ("Boundary", "api.ts · answerQuoteRequest", client_line("answerQuoteRequest"), "POST /api/quotes/requests/{id}/quotes"),
                ("Control", "quotes.py · answer_request", "backend/app/api/quotes.py:173", "Checks that the caller owns the company"),
                ("Control", "quote_service.py · QuoteService.answer", "backend/app/services/quote_service.py:138–165", "Sends version one when the request is PENDING"),
                ("Entity (access)", "quote_repository.py · QuoteRepository.add", "backend/app/repositories/quote_repository.py:58–64", "Stores the version"),
            ],
        ),
        (
            "8.4  An administrator approves an account",
            [
                ("Boundary", "Admin.tsx · change", "frontend/src/pages/Admin.tsx:47", "Runs the chosen action on one account"),
                ("Boundary", "api.ts · adminApprove", client_line("adminApprove"), "POST /api/admin/accounts/{id}/approve"),
                ("Control", "admin.py · approve_account", "backend/app/api/admin.py:52", "Requires the administrator role"),
                ("Control", "account_service.py · AccountService.approve", "backend/app/services/account_service.py:86–90", "Loads the account and calls the entity"),
                ("Entity", "account.py · Account.activate", "backend/app/domain/account.py:39–41", "Sets the status to ACTIVE"),
            ],
        ),
        (
            "8.5  An administrator reads a report",
            [
                ("Boundary", "Platform.tsx · load effect", "frontend/src/pages/Platform.tsx:34", "Reads period and bucket count"),
                ("Boundary", "api.ts · getReport", client_line("getReport"), "GET /api/reports/{period}?buckets={n}"),
                ("Control", "reports.py · read_report", "backend/app/api/reports.py:46", "Requires the administrator role"),
                ("Control", "report_service.py · ReportService.build", "backend/app/services/report_service.py:57–85", "Counts accounts, projects, requests and quotes per bucket"),
                ("Entity (access)", "repositories · all()", "backend/app/repositories", "Supplies the rows to count"),
            ],
        ),
    ]

    for title, steps in walks:
        heading(doc, title, 2)
        rows = [
            [str(index), role, message, place, note]
            for index, (role, message, place, note) in enumerate(steps, start=1)
        ]
        table(doc, ["#", "Role", "Object and function", "Where", "What happens"], rows, [8, 26, 58, 62, 52], size=7.5)


def appendix(doc) -> None:
    heading(doc, "9  Appendix: every file and what it holds", 1)
    body(
        doc,
        "The index answers the reverse question: given a file, which classes and functions "
        "does it contain, and on which lines?",
    )
    files: dict[str, dict] = {}
    for row in DATA["backend"]:
        entry = files.setdefault(row["file"], {"classes": [], "functions": []})
        start, end = row.get("lines", [row["line"], row["line"]])
        label = f"{row['name']} ({start}–{end})" if row["kind"] == "class" else f"{row['name']}() ({start}–{end})"
        entry["classes" if row["kind"] == "class" else "functions"].append(label)
    for relative in sorted(files):
        entry = files[relative]
        parts = entry["classes"] + entry["functions"]
        paragraph = doc.add_paragraph()
        paragraph.paragraph_format.space_after = Pt(1)
        name_run = paragraph.add_run(relative + "  ")
        name_run.bold = True
        name_run.font.size = Pt(8)
        rest = paragraph.add_run(" · ".join(parts) if parts else "—")
        rest.font.size = Pt(8)


def main() -> int:
    doc = Document()
    section = doc.sections[0]
    section.page_width, section.page_height = Mm(210), Mm(297)
    section.left_margin = section.right_margin = Mm(18)
    section.top_margin = section.bottom_margin = Mm(16)

    normal = doc.styles["Normal"]
    normal.font.name = "Calibri"
    normal.font.size = Pt(10)
    normal.paragraph_format.space_after = Pt(4)

    cover(doc)
    introduction(doc)
    entity_section(doc)
    layer_section(
        doc,
        "3",
        "Entity access: backend/app/repositories",
        "repositories",
        "A repository hides the store. A use case asks for 'the project with this id' and the "
        "repository answers with an entity, or with NotFound. Swapping the in-memory store for "
        "a database would change only these classes.",
        40,
    )
    layer_section(
        doc,
        "4",
        "Control: backend/app/services",
        "services",
        "A service is one use case. It checks permission, loads entities through the "
        "repositories, calls entity methods, and returns a result the API layer can send.",
        40,
    )
    layer_section(
        doc,
        "5",
        "Control boundary: backend/app/api",
        "api",
        "A router function is the HTTP edge. It validates the body with a schema, asks the "
        "service to do the work, and translates a domain error into a status code.",
        30,
    )
    schema_section(doc)
    boundary_section(doc)
    sequence_section(doc)
    appendix(doc)

    doc.save(OUT)
    print("wrote", OUT, f"{OUT.stat().st_size // 1024} KB")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
