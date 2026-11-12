# CSIT314 Interior Design Platform

Platform that matches renovation customers to interior designers. Group project for
CSIT314 Software Development Methodologies.

## Testing this build

Testers start with **[TESTING.md](TESTING.md)**. It walks through installing and
running the app with five double-click files and annotated screenshots.

The **[user manual](testing/manual/CSIT314-User-Manual.pdf)** covers every use case for a
customer, a designer and an administrator. It is built from the running app:
`testing/manual/capture_shots.py` takes the screens, `testing/manual/build_manual.py`
writes the document.

The **[code documentation](docs/codebook/CSIT314-Code-Documentation.pdf)** lists every class
and every function with its file and line range, grouped by BCE role, for the class diagram
and the sequence diagrams. Each entry shows a screenshot of the code from a VS Code window
with the `dark-plus` theme. Rebuild it in this order:

```bash
python docs/codebook/parse_code.py          # ast walk -> codebook.json
python docs/codebook/export_snippets.py     # -> render/snippets.json
cd docs/codebook/render && npm i && node render_snippets.mjs snippets.json snippets.html
cd .. && python shoot_snippets.py           # -> shots/*.png
python build_codebook.py                    # -> DOCX, then Word exports the PDF
```

| File | Purpose |
|---|---|
| `1-check-my-pc.bat` | check Git, Node.js and Python are present |
| `2-install.bat` | create the Python environment and install the packages |
| `3-start-app.bat` | start the backend and the frontend, then open the browser |
| `4-load-demo-data.bat` | load the demo data, or the 100-record bulk data |
| `5-stop-app.bat` | stop both servers and free the ports |
| `6-load-my-data.bat` | check and load the tester CSV files in `testing/data` |

## Rebuilding the demonstration dataset

The stores live in process memory, so the catalogue cannot be cloned as a
database file. One committed script rebuilds the exact dataset the walkthrough
and the screen recording were made on:

```
APP_ADMIN_EMAIL=admin@example.com APP_ADMIN_PASSWORD=passw0rd123 \
  backend/.venv/Scripts/python.exe backend/scripts/seed_all.py
```

It runs `seed_demo.py` and then `seed_bulk.py`, and ends with:

```
this month: 125 accounts, 108 projects, 100 requests, 100 quotes
```

`testing/acceptance/check_fresh_clone.py` then walks the seeded app end to end:
it compares the live counts with the dump, signs in as all three roles, sends a
request, answers it, accepts the quote, saves a project, approves a new designer
and uploads a photo. Exit code 0 means every check passed.

`testing/fixtures/video-environment.json` is a read-only dump of that dataset:
125 accounts, 23 companies, 108 projects, 10 categories, 100 quote requests and
the customer's 3 saved projects.
Each photo is analysed through `POST /api/images/tags` while seeding, so the
projects carry the tags the photo search matches on. The dump is there to check
a rebuild and to read the data without starting the app; nothing loads it back.

If another service already holds port 8000, start the backend on another port
and tell the frontend:

```
cd frontend && VITE_API_TARGET=http://127.0.0.1:8010 npm run dev
```

## Stack

| Layer | Choice |
|---|---|
| Frontend | React 18 + Vite + TypeScript |
| Backend | Python 3.11 + FastAPI |
| Data | In memory. No database server. |
| Tests | pytest |
| CI | GitHub Actions |

The backend follows the b-c-e framework:

- **Boundary** - `backend/app/api/` routers and `frontend/src/pages/` screens.
- **Control** - `backend/app/services/` service classes.
- **Entity** - `backend/app/domain/` classes. They hold state and behaviour.

## Layout

```
backend/
  app/
    api/            routers (boundary)
    services/       service classes (control)
    domain/         entities and enums (entity)
    repositories/   in-memory stores
    schemas/        request and response models
  tests/            pytest suites
frontend/
  src/
    pages/          screens
    components/     shared components
    api.ts          typed client for the backend
    auth.tsx        authentication context
```

## Run the backend

```bash
cd backend
python -m venv .venv
.venv/Scripts/python.exe -m pip install -r requirements.txt
.venv/Scripts/python.exe -m uvicorn app.main:app --reload --port 8000
```

The API is served under `http://127.0.0.1:8000/api`. Interactive docs are at
`http://127.0.0.1:8000/docs`.

Environment variables:

| Name | Default | Purpose |
|---|---|---|
| `APP_SECRET_KEY` | development value | JWT signing key. Must be set when `APP_ENV` is not `development`, or the app refuses to start. |
| `APP_TOKEN_MINUTES` | `480` | Access token lifetime in minutes. |
| `APP_ENV` | `development` | Any other value turns on the startup guard. |
| `APP_ADMIN_EMAIL` | unset | Address of the first administrator, created at startup. |
| `APP_ADMIN_PASSWORD` | unset | Password for that administrator. |

Start the backend with an administrator so a designer can be approved:

```bash
APP_ADMIN_EMAIL=admin@example.com APP_ADMIN_PASSWORD=passw0rd123 \
  .venv/Scripts/python.exe -m uvicorn app.main:app --port 8000
```

The store is in memory, so the administrator is created again on every start.

## Run the frontend

```bash
cd frontend
npm install
npm run dev
```

The dev server runs on `http://localhost:5173` and proxies `/api` to the backend.

## Tests

```bash
cd backend
.venv/Scripts/python.exe -m pytest
```

## CI

`.github/workflows/ci.yml` runs the backend tests and the frontend build on every
push and pull request.

## Planned implementations

One line per stage. Tick a line only when the work is merged to `main`, and add
the short commit hash so this list and the history agree.

Both coders update this list in the same commit as their feature. A tick means
"merged and reviewed", not "started". If you build something that is not listed,
add a line with the next number.

### Foundation

- [x] S1 repository ignore rules (`f2f4b38`)
- [x] S2 account slice: register, login, me, roles and status (`0e3bb47`)
- [x] S3 review fixes: session status gate, startup guard, sign in timing (`225dc65`)

### Accounts

- [x] S4 account approval and suspension by an administrator (`eadec74`)
- [x] S5 account administration screen (`9ea66b8`)

### Profile management

- [x] S6 company profile entity, one profile per designer (`bb5e653`)
- [x] S7 company profile service with ownership checks (`03e0671`)
- [x] S8 company profile endpoints, readable by customers (`f5e6d53`)
- [x] S9 designer profile page (`8cc635f`)
- [x] S10 designer detail page for customers (`a89dd7a`)

### Projects

- [x] S11 project entity with style, category, budget band and status (`44bd040`)
- [x] S12 project service with create, edit and delete rules (`4b263b6`)
- [x] S13 project endpoints with owner scoped access (`f300a8d`)
- [x] S14 project editor form with field validation (`49ca8e9`)

### Portfolio

- [x] S15 owner scoped project queries with status and name filters (`b535952`)
- [x] S16 portfolio screen with list, filter and delete actions (`b535952`)

### Search

- [x] S17 project search with keyword, category, style and budget filters (`a91a861`)
- [x] S18 search endpoint with result paging (`38b8756`)
- [x] S19 search screen with filter controls (`744b8ec`)

### Favourites and interest

- [x] S20 shortlist entity, one list per customer (`4a514a5`)
- [x] S21 view and shortlist counters inside the project entity (`4a514a5`)
- [x] S22 shortlist endpoints with add, remove and list (`4a514a5`)
- [x] S23 project detail page with the save action and counter display (`0dedd36`)
- [x] S24 interest summary on the designer portfolio

### Quoting

- [x] S25 quote request entity with pending, answered and cancelled states (`e7e083d`)
- [x] S26 quote service with submit, answer and cancel rules (`e7e083d`)
- [x] S27 quote endpoints for customers and designers (`e7e083d`)
- [x] S28 customer quote screens with submit and cancel (`ee4a982`)
- [x] S29 designer quote inbox with reply (`ee4a982`)

### Platform

- [x] S30 category management with platform manager access (`1e90701`)
- [x] S31 activity reports with daily, weekly and monthly buckets (`1e90701`)
- [x] S32 reporting screen with period selection (`105f0ff`)
- [x] S33 demo seed generator with 100 records per type (`803e3a6`)
- [x] S34 demo walkthrough in this file

### Extensions beyond the plan

Work that was requested after the 34 stages were agreed. It is not part of the
numbered plan above.

- [x]  E1 photo tag suggestions from colour and light, with searchable tags (`bc5dc28`, `9078b41`)
- [x]  E2 photo tags from a 14 MB object model, with a photo search for customers (`fcd22eb`, `7bc2c1d`, `d82a0d4`, `e464d38`, `4c150d6`)
- [x]  E3 consultation appointment scheduler: free slots, one hour bookings, designer accept and cancel

E3 follows the reference class diagram: `ConsultationBookingPage` is
`frontend/src/pages/BookConsultation.tsx`, `ConsultationService` is
`backend/app/services/appointment_service.py`, `ConsultationAppointment` is
`backend/app/domain/appointment.py`, and `ConsultationAppointmentRepository` is
`backend/app/repositories/appointment_repository.py`. A day holds nine hours
(09:00 to 17:00), the diary looks 14 days ahead, and one company holds a slot
once. A booking is either in person at the company's meeting address or an
online call on its call link; the place is copied into the appointment, so a
later profile change does not move an existing booking. The designer accepts a
pending booking, or either party cancels it. The inbox is the notification:
there is no mail server, so the appointment carries `notified_at` instead of a
fake email.

The tag analyser is measured, not assumed. `backend/scripts/evaluate_tags.py`
runs it over COCO val 2017 and checks every tag against the annotation. On 500
room photos and 500 non-room photos it gives 45.0% coverage, 67.3% precision,
4.4% of non-rooms wrongly tagged, and 2.2% of rooms wrongly refused. A photo the
model reads as an animal is refused with "that photo does not look like an
interior" instead of being tagged.

## Demo walkthrough

Six screens carry the whole story. Run them in this order.

**Setup.** Start the backend, then the frontend:

```
cd backend && APP_ADMIN_EMAIL=admin@example.com APP_ADMIN_PASSWORD=passw0rd123 \
  .venv/Scripts/python.exe -m uvicorn app.main:app --port 8000
cd frontend && npm run dev
```

Then load the data. `scripts/seed_demo.py` gives three designers with eight projects.
`scripts/seed_bulk.py` adds 20 designers, 100 customers, 100 projects and 100 quote
requests in about 10 seconds.

**1. A customer searches.** Sign in as `casey@example.com` / `passw0rd123`. Open
"Find a project". Set Room to `Bedroom`, drag the budget handles, then open a card.
The detail page counts the view and offers "Save to shortlist". The Saved link shows
the list.

**1b. A customer searches from a photo.** On the same screen press "Choose a photo"
and pick any room picture. Six tags appear as chips and the list reranks: projects
holding an object tag ("sofa", "dining table") come first, and a project with none is
dropped. Click a chip to remove it and watch the list change.

**2. A designer publishes.** Sign in as `verde@example.com`. "My projects" lists the
portfolio with view and save counts. "New project" takes a title, the fixed room and
style dropdowns, a budget, photo addresses and tags. "Suggest tags from the photo"
reads the first photo and offers palette chips. Accept one, save, then find the
project from the customer account by searching that tag.

**3. A designer answers a request.** Open "Quote inbox". A pending request shows the
scope, the budget band and the target price. Answer with a total, validity days and a
GST position. The version table shows the offer and its expiry date.

**4. A customer negotiates.** Return to the customer. The request shows the quote. Send
a target price with a note. The designer revises, which supersedes the previous
version. Accept the new version. The other open request stays open.

**5. Staff curate the catalogue.** Sign in as `admin@example.com`. "Platform" holds the
category list and the activity report. Add `Rooftop`, see it appear in the customer
dropdown, archive it, see it disappear from the dropdown but stay in the staff list.
Switch the report between daily, weekly and monthly.

**6. Staff apply the rules.** "Admin" lists the accounts. Approve a new designer, then
sign in as that designer. Suspend an account and watch the sign in refuse.

## Working agreement

- One feature branch per person. Merge to `main` after the build is green.
- The API contract lives in `backend/app/schemas/`. Change it in one commit and
  tell the other coder.