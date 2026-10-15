# FieldOps

A data app with a Python backend and a thin React frontend, built so that most of the work stays in Python.

| Part | Stack |
| --- | --- |
| `backend/` | FastAPI, uv, SQLModel + SQLAlchemy (SQLite for dev, **SAP HANA** in production), Alembic migrations, Plotly + pandas for charts |
| `frontend/` | Vite, React, TypeScript, Tailwind + shadcn/ui, TanStack Query, TanStack Router, AG Grid Community, Plotly.js, assistant-ui |

## Running locally

```sh
# Terminal 1: API on http://127.0.0.1:8000 (interactive docs at /docs)
cd backend
uv sync
uv run fastapi dev app/main.py

# Terminal 2: UI on http://localhost:5173 (forwards /api to the backend)
cd frontend
npm install
npm run dev
```

On Windows, App Control (or Smart App Control) may block the `.exe` launchers uv puts in
`backend/.venv/Scripts/`, with `Failed to spawn: fastapi ... os error 4551` or a
`uv trampoline` error. Run the module instead — same thing, no launcher:
`uv run python -m fastapi dev app/main.py`, `uv run python -m pytest`.

## How it fits together

```
Browser (React)                       FastAPI (Python)
───────────────                       ────────────────
routes/items.tsx ── useQuery ──────►  items/router.py ──► items/service.py ──► SQLModel ──► DB
  <DataGrid>      (generated client)                  └─► items/charts.py  (Plotly figure)
  <PlotlyChart>  ◄── figure JSON ─────────────────────────┘
```

- **The backend owns logic, queries, and charts.** Build charts with `plotly.express` just like in Streamlit and return them with `figure_response(fig)`.
- **The frontend displays data.** `<DataGrid>` (AG Grid) shows tables and `<PlotlyChart>` shows backend figures.
- **The API client is generated.** `npm run gen:api` reads FastAPI's OpenAPI schema and writes typed functions to `frontend/src/api/generated/`. If a backend change breaks the frontend, `npm run build` reports it.
- **Service functions are the source of truth.** The REST endpoints call them, and the assistant's tools call the same functions.

See [CLAUDE.md](CLAUDE.md) for the step-by-step recipe for adding a feature.

## Sign-in (bypassed for the demo)

There is no login page: the API treats any request without a session as a built-in **demo
user**, created automatically on first use. Dashboards and chats belong to that user.

The machinery is still there and still works — `app/auth/` hashes passwords, the session
cookie is signed, and data is scoped per user. To require real logins again:

1. Backend: make `require_user` in `app/auth/deps.py` raise 401 instead of returning
   `demo_user(session)` (git history has the original).
2. Frontend: drop the redirect in `src/routes/login.tsx` and restore the `beforeLoad`
   guard, the user name and the sign-out button in `src/routes/__root.tsx`.
3. Create accounts with `uv run python -m app.auth.create_user <name>`, and set
   `SECRET_KEY` in `backend/.env` so sessions survive a restart.

## Dashboards and Explore

- **Dashboard** (`/`): each user's dashboards are grids of tiles. "Edit layout" lets you drag tiles by
  their title bar and resize them; "Add widget" opens a point-and-click builder (dataset, group-bys,
  measures, filters, chart type) with a live preview and a recommended chart.
- **Explore** (`/explore`): ask questions in plain language. The assistant queries the data and draws the
  chart that suits it; if you ask for a chart type it draws that when the data allows, and suggests a
  better one when there is one. Any chart can be pinned with "Add to dashboard", or by asking. Chats are
  saved per user. The header's "Assistant" button opens the same chat in a side panel.

Every widget, whether built by hand or by the assistant, is a **`WidgetSpec`**: a dataset, dimensions,
measures, filters and a chart type. It never contains SQL. The backend turns it into a SQLAlchemy query
using only the fields each feature registers in `app/<feature>/dataset.py` (see `app/analytics/`), so
pinned charts re-run on current data (a "last week" filter keeps meaning last week).

**To make another table chartable**, register it as a dataset. [DEV.md](DEV.md) explains how
specs, datasets and dashboards fit together, and walks through adding one.

```
Explore chat ─► assistant/agent.py (pydantic-ai) ─► tools: analytics/tools.py, dashboards/tools.py
Widget builder ─────────────────────────────────►┐
Dashboard tiles ─── widget_data ─────────────────►├─► analytics/service.py: query.py ► recommend.py ► render.py
                                                   ┘   (WidgetSpec → SQLAlchemy → pandas → Plotly)
```

## Assistant

The assistant uses an OpenAI model through the backend; the browser never sees the key. Create
`backend/.env` with:

```sh
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-4o-mini   # any tool-calling model; larger ones plan multi-step questions better
```

Then restart the API. Without a key the chat still opens and tells you what to set. Its behavior lives in
`backend/app/assistant/prompts.py` and the chart-choice guide `backend/app/assistant/skills/charting.md`.
After changing either, run `uv run python -m evals.charting` (uses your key) to see which charts it picks.

## Database: SQLite for dev, HANA for production

Tables are defined once as SQLModel classes (`backend/app/items/models.py`). SQLAlchemy writes the
dialect-correct SQL for whichever backend is configured, so there is no second copy of the schema and no
SQL to translate. Alembic owns schema changes and runs automatically at startup.

Two places need per-dialect care, because SQLAlchemy's defaults are not portable:

- **Primary keys**: `BigInteger().with_variant(Integer, "sqlite")` plus `Identity()` gives HANA
  `BIGINT GENERATED BY DEFAULT AS IDENTITY` and SQLite an autoincrementing `INTEGER PRIMARY KEY`.
- **Timestamps**: use `TIMESTAMP`, not `DateTime` — the latter renders as `DATETIME`, which HANA rejects.

To switch to HANA: `uv sync --extra hana` (installs `sqlalchemy-hana` and `hdbcli`), then set
`DB_BACKEND=hana` and the `HANA_*` values in `backend/.env`. Not yet tested against a real HANA instance.

```sh
cd backend
uv run python -m app.db.migrate                                  # apply migrations
uv run python -m alembic revision --autogenerate -m "add orders"  # after changing models
uv run python -m alembic check                                    # models and migrations agree?
```

## Checks

```sh
cd backend  && uv run pytest && uv run ruff check .
cd frontend && npm run build && npm run lint
```
