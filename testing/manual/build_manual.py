"""Build the user manual from the captured screens.

Run ``capture_shots.py`` first. This script draws one flow map per role, then
assembles ``CSIT314-User-Manual.docx`` with a cover, a table of contents, one
section per role, and one page per use case.

Usage:

    python testing/manual/build_manual.py
"""

from __future__ import annotations

from datetime import date
from pathlib import Path

from docx import Document
from docx.enum.section import WD_SECTION
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_BREAK
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Mm, Pt, RGBColor
from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).resolve().parent
SHOTS = HERE / "shots"
OUT = HERE / "CSIT314-User-Manual.docx"

INK = RGBColor(0x11, 0x18, 0x27)
MUTED = RGBColor(0x6B, 0x72, 0x80)
ACCENT = RGBColor(0x1F, 0x5C, 0x4A)


# --------------------------------------------------------------------------- flows
def font(size: int) -> ImageFont.FreeTypeFont:
    for name in ("segoeui.ttf", "arial.ttf", "calibri.ttf"):
        for root in (Path("C:/Windows/Fonts"), Path("/usr/share/fonts/truetype")):
            candidate = root / name
            if candidate.exists():
                return ImageFont.truetype(str(candidate), size)
    return ImageFont.load_default()


def draw_flow(title: str, steps: list[str], path: Path) -> None:
    """Draw a vertical flow: numbered boxes joined by arrows."""
    width, box_h, gap = 1000, 84, 46
    height = 92 + len(steps) * (box_h + gap) + 24
    image = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(image)
    title_font, step_font = font(30), font(23)

    draw.text((40, 26), title, fill=(17, 24, 39), font=title_font)
    y = 92
    for index, text in enumerate(steps, start=1):
        draw.rounded_rectangle(
            (40, y, width - 40, y + box_h),
            radius=14,
            outline=(31, 92, 74),
            width=3,
            fill=(246, 249, 247),
        )
        draw.ellipse((58, y + 22, 98, y + 62), fill=(31, 92, 74))
        number = str(index)
        draw.text(
            (78 - draw.textlength(number, font=step_font) / 2, y + 27),
            number,
            fill="white",
            font=step_font,
        )
        draw.text((116, y + 25), text, fill=(17, 24, 39), font=step_font)
        if index < len(steps):
            cx = width // 2
            draw.line((cx, y + box_h, cx, y + box_h + gap - 8), fill=(31, 92, 74), width=3)
            draw.polygon(
                [
                    (cx - 9, y + box_h + gap - 16),
                    (cx + 9, y + box_h + gap - 16),
                    (cx, y + box_h + gap - 2),
                ],
                fill=(31, 92, 74),
            )
        y += box_h + gap

    image.save(path)
    print("drew", path.name)


# ----------------------------------------------------------------------- docx help
def set_cell_shading(cell, hex_colour: str) -> None:
    shade = OxmlElement("w:shd")
    shade.set(qn("w:fill"), hex_colour)
    cell._tc.get_or_add_tcPr().append(shade)


def add_field(paragraph, instruction: str) -> None:
    run = paragraph.add_run()
    begin = OxmlElement("w:fldChar")
    begin.set(qn("w:fldCharType"), "begin")
    instr = OxmlElement("w:instrText")
    instr.set(qn("xml:space"), "preserve")
    instr.text = instruction
    end = OxmlElement("w:fldChar")
    end.set(qn("w:fldCharType"), "end")
    run._r.append(begin)
    run._r.append(instr)
    run._r.append(end)


def heading(doc: Document, text: str, level: int) -> None:
    paragraph = doc.add_heading(text, level=level)
    for run in paragraph.runs:
        run.font.color.rgb = INK if level == 1 else ACCENT
        run.font.name = "Calibri"


def body(doc: Document, text: str, size: float = 10.5, space_after: int = 6) -> None:
    paragraph = doc.add_paragraph()
    run = paragraph.add_run(text)
    run.font.size = Pt(size)
    paragraph.paragraph_format.space_after = Pt(space_after)


def steps(doc: Document, items: list[str]) -> None:
    for index, item in enumerate(items, start=1):
        paragraph = doc.add_paragraph()
        paragraph.paragraph_format.left_indent = Mm(8)
        paragraph.paragraph_format.first_line_indent = Mm(-8)
        paragraph.paragraph_format.space_after = Pt(3)
        number = paragraph.add_run(f"{index}.  ")
        number.bold = True
        number.font.size = Pt(10.5)
        text = paragraph.add_run(item)
        text.font.size = Pt(10.5)


def figure(doc: Document, name: str, caption: str, width_mm: int = 150) -> None:
    path = SHOTS / name
    if not path.exists():
        raise SystemExit(f"missing screenshot: {path}")
    doc.add_picture(str(path), width=Mm(width_mm))
    doc.paragraphs[-1].alignment = WD_ALIGN_PARAGRAPH.CENTER
    note = doc.add_paragraph()
    note.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = note.add_run(caption)
    run.italic = True
    run.font.size = Pt(8.5)
    run.font.color.rgb = MUTED
    note.paragraph_format.space_after = Pt(10)


def use_case(
    doc: Document,
    title: str,
    goal: str,
    where: str,
    todo: list[str],
    result: str,
    shot: str | None = None,
    caption: str = "",
) -> None:
    # One use case per page: the steps and the screen they describe stay together.
    page_break(doc)
    heading(doc, title, 2)
    label = doc.add_paragraph()
    label.paragraph_format.space_after = Pt(2)
    tag = label.add_run(f"Where: {where}")
    tag.italic = True
    tag.font.size = Pt(9.5)
    tag.font.color.rgb = MUTED

    body(doc, goal)
    steps(doc, todo)

    outcome = doc.add_paragraph()
    outcome.paragraph_format.space_before = Pt(4)
    lead = outcome.add_run("Result: ")
    lead.bold = True
    lead.font.size = Pt(10.5)
    lead.font.color.rgb = ACCENT
    rest = outcome.add_run(result)
    rest.font.size = Pt(10.5)

    if shot is not None:
        figure(doc, shot, caption)


def table(doc: Document, header: list[str], rows: list[list[str]], widths: list[int]) -> None:
    grid = doc.add_table(rows=1, cols=len(header))
    grid.style = "Table Grid"
    grid.alignment = WD_TABLE_ALIGNMENT.CENTER
    for index, text in enumerate(header):
        cell = grid.rows[0].cells[index]
        cell.text = ""
        run = cell.paragraphs[0].add_run(text)
        run.bold = True
        run.font.size = Pt(9.5)
        set_cell_shading(cell, "EAF1ED")
    for row in rows:
        cells = grid.add_row().cells
        for index, text in enumerate(row):
            cells[index].text = ""
            run = cells[index].paragraphs[0].add_run(text)
            run.font.size = Pt(9.5)
    for row in grid.rows:
        for index, width in enumerate(widths):
            row.cells[index].width = Mm(width)
    doc.add_paragraph().paragraph_format.space_after = Pt(2)


def page_break(doc: Document) -> None:
    doc.add_paragraph().add_run().add_break(WD_BREAK.PAGE)


# ---------------------------------------------------------------------------- build
def main() -> int:
    flows = SHOTS / "flow-customer.png"
    draw_flow(
        "Customer flow",
        [
            "Sign in or register",
            "Dashboard: check the account and its status",
            "Find a project: filter by keyword, room, style, budget",
            "Search by photo: upload a room, read the tags",
            "Open a project and read the designer's details",
            "Save to shortlist for later",
            "Request a quote from the designer",
            "Compare the versions and accept one",
        ],
        flows,
    )
    draw_flow(
        "Designer flow",
        [
            "Sign in",
            "Company profile: name, place, contact",
            "Create Project: photos, tags, budget",
            "My Projects: edit, mark as past, delete",
            "Quote inbox: requests from customers",
            "Answer with a total, a validity window and a note",
            "Revise when the customer sends a target price",
            "Public designer page shows the portfolio",
        ],
        SHOTS / "flow-designer.png",
    )
    draw_flow(
        "Administrator flow",
        [
            "Sign in as an administrator",
            "Admin: filter accounts by status",
            "Approve a designer or suspend an account",
            "Platform: add a category or archive one",
            "Platform: read the daily, weekly or monthly report",
            "Export the same numbers from the API when needed",
        ],
        SHOTS / "flow-admin.png",
    )

    doc = Document()

    # Page setup: A4 with room for 168 mm figures.
    section = doc.sections[0]
    section.page_width, section.page_height = Mm(210), Mm(297)
    section.left_margin = section.right_margin = Mm(21)
    section.top_margin = section.bottom_margin = Mm(18)

    normal = doc.styles["Normal"]
    normal.font.name = "Calibri"
    normal.font.size = Pt(10.5)
    normal.paragraph_format.space_after = Pt(6)

    footer = section.footer.paragraphs[0]
    footer.alignment = WD_ALIGN_PARAGRAPH.CENTER
    add_field(footer, "PAGE")
    footer.runs[0].font.size = Pt(8.5)
    footer.runs[0].font.color.rgb = MUTED

    # ----- cover
    spacer = doc.add_paragraph()
    spacer.paragraph_format.space_before = Pt(90)
    title = doc.add_paragraph()
    title_run = title.add_run("Interior Design Platform")
    title_run.bold = True
    title_run.font.size = Pt(34)
    title_run.font.color.rgb = INK

    subtitle = doc.add_paragraph()
    sub_run = subtitle.add_run("User manual and screen guide")
    sub_run.font.size = Pt(16)
    sub_run.font.color.rgb = ACCENT

    body(doc, "Every use case, for customers, designers and administrators.", 11)
    body(
        doc,
        f"CSIT314 Software Engineering Project · {date.today().strftime('%d %B %Y')}",
        10,
    )
    body(
        doc,
        "All screens in this manual were captured from the running application "
        "against the seeded demonstration data.",
        9,
    )
    page_break(doc)

    # ----- contents
    contents_title = doc.add_paragraph()
    contents_run = contents_title.add_run("Contents")
    contents_run.bold = True
    contents_run.font.size = Pt(18)
    contents_run.font.color.rgb = INK
    paragraph = doc.add_paragraph()
    add_field(paragraph, 'TOC \\o "1-2" \\h \\z \\u')
    body(doc, "Page numbers refer to the printed layout of this manual.", 9)
    page_break(doc)

    # ----- 1 about
    heading(doc, "1  About this manual", 1)
    body(
        doc,
        "This manual explains what a person can do in the platform and where to do it. "
        "It is written for the three roles the platform supports. Each use case gives the "
        "screen, the steps, and the result to expect.",
    )
    body(
        doc,
        "The application is a teaching build. Records live in the memory of the backend "
        "process, so a restart empties the catalogue. Section 2 explains how to restore it.",
    )

    heading(doc, "1.1  The three roles", 2)
    table(
        doc,
        ["Role", "Can do", "Cannot do"],
        [
            [
                "Customer",
                "Browse and search the catalogue, search by photo, save projects, request quotes, accept or decline a quote, name a target price, book and cancel a consultation",
                "Publish projects, answer quotes, manage accounts",
            ],
            [
                "Designer (IDM)",
                "Publish and edit projects, upload photos, read tags, set the company profile with a meeting address and a call link, answer and revise quotes, accept or cancel a consultation",
                "Approve accounts, manage categories, read platform reports",
            ],
            [
                "Platform manager",
                "Approve or suspend accounts, add, archive and restore categories, read activity reports",
                "Publish projects, send or answer quotes",
            ],
        ],
        [30, 78, 60],
    )

    heading(doc, "1.2  Demonstration accounts", 2)
    body(
        doc,
        "Every demonstration account uses the password passw0rd123. The administrator "
        "account is created from APP_ADMIN_EMAIL and APP_ADMIN_PASSWORD at startup.",
    )
    table(
        doc,
        ["Role", "Email", "What it shows"],
        [
            ["Platform manager", "admin@example.com", "Approval queue, categories, reports"],
            ["Designer", "verde@example.com", "Studio Verde: company profile and portfolio"],
            ["Designer", "designer000@example.com", "A bulk designer with a large portfolio"],
            ["Customer", "casey@example.com", "A customer with a saved shortlist and one answered request"],
        ],
        [34, 58, 76],
    )

    # ----- 2 running
    heading(doc, "2  Getting the platform running", 1)
    body(
        doc,
        "One clone, one install, two commands. The repository contains the seed scripts, so "
        "the catalogue can be rebuilt on any machine in about a minute.",
    )
    steps(
        doc,
        [
            "Double-click 1-check-my-pc.bat to confirm the tools are present.",
            "Double-click 2-install.bat to create the Python environment and install the front end.",
            "Double-click 3-start-app.bat. Two windows open: the API on port 8000 and the site on port 5173.",
            "Double-click 4-load-demo-data.bat to rebuild the recorded dataset.",
            "Open http://localhost:5173 and sign in with a demonstration account.",
            "Double-click 5-stop-app.bat when finished.",
        ],
    )
    body(
        doc,
        "If another program already holds port 8000, start the API on another port and point the "
        "front end at it: set VITE_API_TARGET=http://127.0.0.1:8010 before npm run dev.",
        10,
    )

    # ----- 3 customer
    page_break(doc)
    heading(doc, "3  Customer", 1)
    body(
        doc,
        "A customer looks for a designer whose work fits a room, keeps the ones worth a "
        "second look, and asks for a price.",
    )
    figure(doc, "flow-customer.png", "Figure 1  The customer journey from sign in to an accepted quote.", 150)

    use_case(
        doc,
        "3.1  Create an account and sign in",
        "You need an account to save projects or send a request. Browsing the catalogue does not need one.",
        "Create account, then Sign in",
        [
            "Open the site and press Create account in the top navigation.",
            "Enter your name, your email address and a password.",
            "Press Create account. New accounts start as Pending for a designer, active for a customer.",
            "Sign in with the same email address and password.",
        ],
        "The dashboard opens with your name in the navigation bar.",
        "02-register.png",
        "Figure 2  The registration form. The role field decides which screens appear after sign in.",
    )

    use_case(
        doc,
        "3.2  Check your account on the dashboard",
        "The dashboard confirms which account is signed in and whether it can act.",
        "Dashboard",
        [
            "Press Dashboard in the top navigation.",
            "Read Display name, Email, Role and Status.",
            "Read Account ID and Member since when support asks for them.",
            "If a notice appears above the card, read it: a pending designer cannot publish yet.",
        ],
        "You can see the account state at a glance. Saved work and requests have their own links in the top navigation.",
        "03-customer-dashboard.png",
        "Figure 3  The dashboard: one card with the account details and its status.",
    )

    use_case(
        doc,
        "3.3  Find a project with filters",
        "The catalogue holds every published project. Filters narrow it to the rooms and styles that matter.",
        "Find a project",
        [
            "Press Find a project in the top navigation.",
            "Type a word in Keyword to match the title, the description or a tag.",
            "Choose a Room and a Style, or leave them on All rooms and All styles.",
            "Drag the Budget sliders to the range you can spend.",
            "Press Search. The count above the results shows how many projects matched.",
        ],
        "Each card shows the room, the style, the price range, the tags and the designer.",
        "04b-customer-search.png",
        "Figure 4  The catalogue with the filter panel and the ranked result count.",
    )

    use_case(
        doc,
        "3.4  Search by photo",
        "Sometimes a picture says what words cannot. Upload a room you like and the platform reads the objects in it.",
        "Find a project, then Find similar from a photo",
        [
            "Press Choose a photo and pick a JPEG, PNG or WebP image up to 5 MB.",
            "The photo appears under Your reference photo. No button is needed: the reading starts at once.",
            "Read the tags under the photo. A tag you do not want can be removed with its x.",
            "The results below are ranked by how many tags they share with the photo.",
        ],
        "A bedroom photo returns sofa, sliding door, bed, moody, neutral palette and busy detail, and the catalogue drops to the projects that share those tags.",
        "04-customer-photo-search.png",
        "Figure 5  A photo search. Six tags were read; the list is ranked by tag match.",
    )

    use_case(
        doc,
        "3.5  Open a project and read the details",
        "Before saving or asking for a price, check the budget, the scope and the designer.",
        "Any project card",
        [
            "Press the project title on a card.",
            "Read the description, the budget range and the tags.",
            "Press View designer to read the company profile and the rest of that portfolio.",
        ],
        "The project page shows who made it, what it costs and how it looks.",
        "05-customer-project.png",
        "Figure 6  A project page with its photographs, budget and designer.",
    )

    use_case(
        doc,
        "3.6  Save a project to the shortlist",
        "A shortlist keeps the candidates together while you compare them.",
        "A project page",
        [
            "Press Save to shortlist on the project page.",
            "The button changes to Saved — remove, so the same press undoes it.",
            "Press Saved in the top navigation to see the whole list.",
        ],
        "The project stays in Saved until you remove it. The designer sees the count.",
        "06-customer-saved.png",
        "Figure 7  The shortlist. Each card links back to the project.",
    )

    use_case(
        doc,
        "3.7  Request a quote",
        "A request states the work and the budget. The designer answers with a total.",
        "A designer page, then Request a quote",
        [
            "Open the designer page from a project or from Designers.",
            "Press Request a quote.",
            "Give the request a title and describe the scope in your own words.",
            "Enter the budget floor and ceiling, and an optional target price.",
            "Press Send request.",
        ],
        "The request appears under Requests as Pending until the designer answers.",
        "07-customer-request-quote.png",
        "Figure 8  The request form. The scope is what the designer prices.",
    )

    use_case(
        doc,
        "3.8  Compare, counter and accept a quote",
        "Every answer is kept as a version, so you can see what changed and why.",
        "Requests, then one request",
        [
            "Open Requests and choose the request.",
            "Read the Scopes card, then the Versions table: total, GST, valid until, state and note.",
            "To negotiate, type a target price and press Send target. The designer may answer with a new version.",
            "Press Accept quote to accept the current version, or Decline quote with a reason.",
        ],
        "An accepted quote is marked Accepted and the rest of the versions stay visible for the record.",
        "08-customer-quote.png",
        "Figure 9  A quote with one version, the GST line, the validity date and the decision panel.",
    )

    use_case(
        doc,
        "3.9  Book a consultation",
        "A consultation is one hour with the designer, before any work is agreed.",
        "Designers, then a studio, Book a consultation",
        [
            "Open Designers and choose a studio.",
            "Press Book a consultation under the company details.",
            "Choose Where: In person or Video call. The line under it shows the meeting address or the call link.",
            "Choose a Day. The list covers the next 14 days.",
            "Press one free Time. One hour is one slot, and a taken hour is not offered.",
            "Write what you need in the box, then press Book this time.",
            "Read the confirmation, then press View my appointments.",
        ],
        "The hour is held as Pending with its meeting place. The designer sees it in Consultations and confirms it.",
        "19-customer-booking.png",
        "Figure 10  The booking page: the meeting type, the day list, the free hours and the requirements box.",
    )

    use_case(
        doc,
        "3.10  Cancel a consultation",
        "A booked hour can be given back. The record stays, so both parties keep the history.",
        "Appointments",
        [
            "Press Appointments in the top navigation.",
            "Find the row by Designer, Day and Time.",
            "Read the Where column: it shows the meeting address or the call link.",
            "Press Cancel on that row.",
            "Read the State column: the row now says Cancelled and the hour returns to the designer.",
        ],
        "The cancelled hour is offered again to other customers on the booking page.",
        "20-customer-appointments.png",
        "Figure 11  The customer's appointment list with the state of each booking.",
    )

    # ----- 4 designer
    page_break(doc)
    heading(doc, "4  Designer (IDM)", 1)
    body(
        doc,
        "A designer publishes work, keeps the portfolio current, and answers the requests that "
        "customers send.",
    )
    figure(doc, "flow-designer.png", "Figure 12  The designer journey from profile to an answered request.", 150)

    use_case(
        doc,
        "4.1  Check the designer account",
        "The dashboard shows the account state. A designer must be active before a project can be published.",
        "Dashboard",
        [
            "Sign in with a designer account.",
            "Read Display name, Email, Role, Status, Account ID and Member since.",
            "A Pending notice means an administrator has not approved the account yet.",
            "A Suspended notice means the account cannot publish until an administrator restores it.",
        ],
        "The account card states exactly what the platform will let this account do.",
        "09-designer-dashboard.png",
        "Figure 13  The designer dashboard.",
    )

    use_case(
        doc,
        "4.2  Complete the company profile",
        "The profile is what a customer reads before sending a request.",
        "Company profile",
        [
            "Press Company profile in the top navigation.",
            "Enter the studio name, the city, a short description, a contact email and a phone number.",
            "Enter the Meeting address for in person consultations, and the Video call link for online ones.",
            "Press Save profile.",
        ],
        "The profile appears on the public designer page and beside every project. A customer reads the meeting address and the call link there.",
        "14-designer-company.png",
        "Figure 14  The company profile form.",
    )

    use_case(
        doc,
        "4.3  Publish a project with photos and tags",
        "Photographs carry the work; the tags make it findable.",
        "Create Project",
        [
            "Press Create Project in the top navigation.",
            "Give the project a title and a description, then choose a category and a style.",
            "Enter the budget floor and ceiling.",
            "Press + Add photo and pick up to eight images. Each upload adds to the queue; it does not replace the last one.",
            "Read Suggested from your photos. Press a chip to add that tag to Description tags, and press the x on a photo to remove it.",
            "Press Create Project.",
        ],
        "The project appears in My Projects and in the catalogue, with the tags you kept.",
        "10-designer-project-editor.png",
        "Figure 15  Two photos in the queue, the tags they suggested, and the empty tag field waiting for a choice.",
    )

    use_case(
        doc,
        "4.4  Manage the portfolio",
        "Projects change: prices move, work finishes, a mistake must go.",
        "My Projects",
        [
            "Press My Projects in the top navigation.",
            "Use the search box and the status filter to find a project.",
            "Press Edit to change the details, the photos or the tags.",
            "Press Mark as Past when the work is finished, or Delete to remove it.",
        ],
        "Counts on the card update as customers view and save the work.",
        "11-designer-projects.png",
        "Figure 16  My Projects with views, saves and the actions for each row.",
    )

    use_case(
        doc,
        "4.5  Answer a quote request",
        "An answer is one total, one validity window and an optional note.",
        "Quote inbox, then one request",
        [
            "Press Quote inbox in the top navigation.",
            "Open the request you want to answer.",
            "Read the scope and the budget the customer gave.",
            "Enter the total, choose how many days the quote stays valid, and say whether GST is included.",
            "Add a note, then press Send quote.",
        ],
        "The request moves to Answered and the customer sees version one. A later answer becomes version two.",
        "13-designer-answer.png",
        "Figure 17  One request with its versions and the answer form.",
    )

    use_case(
        doc,
        "4.6  Read the public designer page",
        "This is the page a customer reaches from Designers.",
        "Designers, then a studio",
        [
            "Open Designers from the top navigation.",
            "Press a studio name.",
            "Read the description, the contact details and the projects underneath.",
        ],
        "The portfolio shows every published project with its tags and price range.",
        "15-designer-portfolio.png",
        "Figure 18  The public page for Studio Verde.",
    )

    use_case(
        doc,
        "4.7  Accept or cancel a consultation",
        "The consultation inbox is the designer's diary for the next two weeks.",
        "Consultations",
        [
            "Press Consultations in the top navigation.",
            "Read Customer, Day, Time, Where, What they need and State.",
            "Press Accept to confirm a Pending booking. The customer sees Accepted on Appointments.",
            "Press Cancel to give the hour back. The row stays as Cancelled.",
        ],
        "A Pending booking becomes Accepted, and the customer reads that state on their own list.",
        "21-designer-appointments.png",
        "Figure 19  The designer's consultation inbox with a pending booking and its two actions.",
    )

    # ----- 5 admin
    page_break(doc)
    heading(doc, "5  Administrator", 1)
    body(
        doc,
        "The administrator keeps the platform tidy: accounts are approved, categories stay "
        "current and activity is measured.",
    )
    figure(doc, "flow-admin.png", "Figure 20  The administrator journey.", 150)

    use_case(
        doc,
        "5.1  Approve and suspend accounts",
        "A designer cannot publish until an administrator approves the account.",
        "Admin",
        [
            "Press Admin in the top navigation.",
            "Choose a status in Show: Pending, Active, Suspended or all.",
            "Find the account and press Approve to let it in, or Suspend to stop it.",
            "Press Show again to confirm the new status.",
        ],
        "An approved designer can sign in and publish. A suspended account cannot.",
        "17-admin-accounts.png",
        "Figure 21  The account list with its status filter and the approve and suspend actions.",
    )

    use_case(
        doc,
        "5.2  Manage categories",
        "Categories are how customers filter the catalogue. They are archived, never deleted, so old projects keep a valid label.",
        "Platform, Categories",
        [
            "Press Platform in the top navigation.",
            "Type a name under New category and press Add.",
            "Press Archive beside a category to retire it, or Restore to bring it back.",
        ],
        "The category list on the project form follows these states.",
        "16-admin-platform.png",
        "Figure 22  Platform management: the category list with Add, Archive and the state of each row.",
    )

    use_case(
        doc,
        "5.3  Read the activity report",
        "The report answers a simple question: is the platform being used, and how much?",
        "Platform, Activity reports",
        [
            "Scroll to Activity reports on the Platform page.",
            "Choose a Period: daily, weekly or monthly.",
            "Choose how many Buckets to show, for example 14 days or 30 days.",
            "Read the columns: accounts, projects, requests and quotes per bucket.",
        ],
        "The newest bucket shows the current totals. The same numbers are served by GET /api/reports?period=weekly&buckets=6 for a script.",
        "18-admin-reports.png",
        "Figure 23  A daily report. The last row carries the current totals.",
    )

    # ----- 6 reference
    page_break(doc)
    heading(doc, "6  Reference", 1)

    heading(doc, "6.1  Ports and addresses", 2)
    table(
        doc,
        ["Service", "Address", "Note"],
        [
            ["Front end", "http://localhost:5173", "Vite dev server"],
            ["API", "http://127.0.0.1:8000", "FastAPI; set another port with the uvicorn flag"],
            ["API documentation", "http://127.0.0.1:8000/docs", "Every endpoint with a Try it out button"],
            ["Uploaded photos", "http://127.0.0.1:8000/uploads/...", "Served from backend/uploads"],
        ],
        [40, 68, 60],
    )

    heading(doc, "6.2  Where the data lives", 2)
    body(
        doc,
        "Accounts, companies, projects, requests, quotes, appointments and categories live in the memory of "
        "the backend process. A restart empties them. The repository carries the rebuild:",
    )
    steps(
        doc,
        [
            "backend/scripts/seed_all.py runs the demo seed and then the bulk seed.",
            "The result is 125 accounts, 23 companies, 108 projects, 100 requests and 100 quotes.",
            "testing/fixtures/video-environment.json records that dataset for comparison.",
        ],
    )
    body(
        doc,
        "Uploaded photos are the exception: they are files under backend/uploads, which is "
        "ignored by git. They stay after a restart even when the rows that pointed at them do not.",
        10,
    )

    heading(doc, "6.3  When something looks wrong", 2)
    table(
        doc,
        ["Symptom", "Cause", "Fix"],
        [
            [
                "The catalogue is empty",
                "The backend restarted",
                "Run 4-load-demo-data.bat, or seed_all.py",
            ],
            [
                "Cannot reach the server",
                "The API is not running, or on another port",
                "Start it, and set VITE_API_TARGET to match",
            ],
            [
                "A photo does not appear after upload",
                "The file is larger than 5 MB or not an image",
                "Use a JPEG, PNG or WebP under 5 MB",
            ],
            [
                "Login says the password is wrong",
                "The account was seeded with another password",
                "Use passw0rd123, or register again",
            ],
        ],
        [50, 55, 63],
    )

    body(doc, "End of manual.", 9)

    doc.save(OUT)
    print("wrote", OUT, f"{OUT.stat().st_size // 1024} KB")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
