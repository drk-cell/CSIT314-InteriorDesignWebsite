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
| `APP_SECRET_KEY` | `dev-only-change-me` | JWT signing key. Set this outside local development. |
| `APP_TOKEN_MINUTES` | `480` | Access token lifetime in minutes. |

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

## Working agreement

- One feature branch per person. Merge to `main` after the build is green.
- The API contract lives in `backend/app/schemas/`. Change it in one commit and
  tell the other coder.