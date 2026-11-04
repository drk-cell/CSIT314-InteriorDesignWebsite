# CSIT314 Interior Design Platform

Platform that matches renovation customers to interior designers. Group project for
CSIT314 Software Development Methodologies.

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

- [ ] S11 project entity with style, category, budget band and status
- [ ] S12 project service with create, edit and delete rules
- [ ] S13 project endpoints with owner scoped access
- [ ] S14 project editor form with field validation

### Portfolio

- [ ] S15 owner scoped project queries with status and name filters
- [ ] S16 portfolio screen with list, filter and delete actions

### Search

- [ ] S17 project search with keyword, category, style and budget filters
- [ ] S18 search endpoint with result paging
- [ ] S19 search screen with filter controls

### Favourites and interest

- [ ] S20 shortlist entity, one list per customer
- [ ] S21 view and shortlist counters inside the project entity
- [ ] S22 shortlist endpoints with add, remove and list
- [ ] S23 project detail page with the save action and counter display
- [ ] S24 interest summary on the designer portfolio

### Quoting

- [ ] S25 quote request entity with pending, answered and cancelled states
- [ ] S26 quote service with submit, answer and cancel rules
- [ ] S27 quote endpoints for customers and designers
- [ ] S28 customer quote screens with submit and cancel
- [ ] S29 designer quote inbox with reply

### Platform

- [ ] S30 category management with platform manager access
- [ ] S31 activity reports with daily, weekly and monthly buckets
- [ ] S32 reporting screen with period selection
- [ ] S33 demo seed generator with 100 records per type
- [ ] S34 demo walkthrough in this file

## Working agreement

- One feature branch per person. Merge to `main` after the build is green.
- The API contract lives in `backend/app/schemas/`. Change it in one commit and
  tell the other coder.