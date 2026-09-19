# FieldOps: guide for contributors and AI assistants

This app replaces a Streamlit app. Its maintainers are mainly Python developers, so:

- **Keep logic in Python.** Queries, calculations, and Plotly charts belong in the backend. The frontend fetches and displays.
- **Choose boring, popular solutions.** Don't add frontend state libraries, custom hooks frameworks, or clever abstractions. Match the existing examples.
- **Use `items` as the reference feature.** Copy its structure for new features.

## Adding a feature (e.g. "orders")

1. **Models**: `backend/app/orders/models.py` holds the SQLModel classes — one `table=True` model plus the API shapes (`OrderBase`, `Order`, `OrderCreate`, `OrderUpdate`, `OrderPublic`). Copy `app/items/models.py`. These class names become the generated frontend type names.
2. **Migration**: import the new models in `backend/migrations/env.py`, then `uv run python -m alembic revision --autogenerate -m "add orders"`. Read the generated file before trusting it, and keep the numbering (`000N_add_orders.py`). Migrations run automatically at startup; never edit an applied one, add a new one instead.
3. **Service**: `backend/app/orders/service.py` holds plain functions that take a `Session` and run SQLModel `select()` queries. All data access and business logic goes here.
4. **Charts** (optional): `backend/app/orders/charts.py` holds functions that take a `Session` and return a Plotly `Figure` (use `plotly.express` + pandas).
5. **Router**: in `backend/app/orders/router.py`, keep endpoints thin, return charts with `figure_response(fig)`, and include the router in `app/main.py`.
   The endpoint **function name becomes the frontend function name** (`list_orders` → `listOrdersOptions`), so it must be unique app-wide.
6. **Test**: add `backend/tests/test_orders.py` and run `uv run pytest`. Tests get a fresh SQLite file per test and migrations run for them, so seeded rows are present.
7. **Regenerate the client**: from `frontend/`, run `npm run gen:api`. Never hand-edit `src/api/generated/`.
8. **Page**: add `frontend/src/routes/orders.tsx` (the file name is the URL) and a link in `src/routes/__root.tsx`.
   - Load data: `useQuery(listOrdersOptions())`
   - Save data: `useMutation(createOrderMutation())`. After any successful mutation, on-screen data refetches automatically (see `src/lib/queryClient.ts`).
   - Tables: `<DataGrid>` (AG Grid). For editing, handle `onCellEditRequest` by calling an update mutation (see `routes/items.tsx`).
   - Charts: `<PlotlyChart figure={...} />` with a chart endpoint.
   - UI pieces: shadcn components in `src/components/ui/` (add more with `npx shadcn@latest add <name>`).
9. **Check**: `npm run build && npm run lint` in `frontend/`, and `uv run ruff check .` in `backend/`.

## Conventions

- **Queries go through SQLModel/SQLAlchemy**, never hand-written SQL strings. SQLAlchemy emits the right dialect for SQLite and HANA, which is what keeps the two backends in sync. If you genuinely need raw SQL, wrap it in `text()` and check it on both.
- Tables and columns are **lowercase**; SQLAlchemy quotes them consistently on both backends.
- Two column types need per-dialect handling (see `app/items/models.py`): primary keys use `BigInteger().with_variant(Integer, "sqlite")` + `Identity()`, and timestamps use `TIMESTAMP` rather than `DateTime` (which renders as `DATETIME` and fails on HANA).
- The endpoint takes a `DbSession` (`app/db/__init__.py`). One session per request, committed on success and rolled back on error, so service functions only need `flush()` to get a generated id.
- Model docstrings become `description` text in `openapi.json`, so keep them to one line.
- Frontend imports use `@/` for `src/`.
- AG Grid: `readOnlyEdit` is on, so the grid never changes data itself; the API is the source of truth.
- Don't add Redux, Zustand, or other client state libraries without a clear need. Server data lives in TanStack Query, and simple UI state lives in `useState` or the URL.

## Commands

| Where | Command | What |
| --- | --- | --- |
| backend | `uv run fastapi dev app/main.py` | API with reload on :8000 |
| backend | `uv run pytest` / `uv run ruff check .` / `uv run ruff format .` | Tests, lint, format |
| backend | `uv run python -m app.db.migrate` | Apply migrations manually |
| backend | `uv run python -m alembic revision --autogenerate -m "..."` | New migration from model changes |
| backend | `uv run python -m alembic check` | Fail if models and migrations disagree |
| frontend | `npm run dev` | UI on :5173 |
| frontend | `npm run gen:api` | Regenerate the API client from the backend |
| frontend | `npm run build` / `npm run lint` | Type-check + build, lint |

## Assistant panel

The chat panel (header → "Assistant") talks to OpenAI through the backend; the browser never sees the API key.

- `backend/app/assistant/prompts.py` — the system prompt. Edit this to change the assistant's behavior.
- `backend/app/assistant/service.py` — calls OpenAI and yields text chunks.
- `backend/app/assistant/router.py` — `GET /api/assistant/status`, `POST /api/assistant/chat` (streams plain text).
- `frontend/src/lib/assistantAdapter.ts` — ~40 lines connecting assistant-ui to that endpoint.
- `frontend/src/components/assistant-ui/` — chat UI generated by `npx assistant-ui@latest add thread`. Edit it like shadcn components. Note: the CLI writes files flat into `src/components/`, so move any new `*.aui.tsx` into `src/components/assistant-ui/elements/`, which is where they import each other from.
- Do **not** use `@assistant-ui/react-ui`; that package is behind `@assistant-ui/react` and fails to build.

Config lives in `backend/.env`: `OPENAI_API_KEY` (required), `OPENAI_MODEL`, and `OPENAI_BASE_URL` for Azure or another OpenAI-compatible gateway.

## Planned

- Give the assistant tools: define OpenAI tools in `backend/app/<feature>/tools.py` that call the same `service.py`/`charts.py` functions, run them in `assistant/service.py`, and render results in chat with `<DataGrid>` and `<PlotlyChart>`.
