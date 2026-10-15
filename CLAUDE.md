# FieldOps: guide for contributors and AI assistants

This app replaces a Streamlit app. Its maintainers are mainly Python developers, so:

- **Keep logic in Python.** Queries, calculations, and Plotly charts belong in the backend. The frontend fetches and displays.
- **Choose boring, popular solutions.** Don't add frontend state libraries, custom hooks frameworks, or clever abstractions. Match the existing examples.
- **Use `items` as the reference feature.** Copy its structure for new features.

**Before changing anything, read [TODO.md](TODO.md)** — known bugs, gaps and pending
decisions live there. Update it as part of the work, and move finished items to
[DONE.md](DONE.md) (dated, newest first) so TODO.md stays short. Don't read DONE.md up front;
search it when you need the history of a decision.

## Adding a feature (e.g. "orders")

1. **Models**: `backend/app/orders/models.py` holds the SQLModel classes — one `table=True` model plus the API shapes (`OrderBase`, `Order`, `OrderCreate`, `OrderUpdate`, `OrderPublic`). Copy `app/items/models.py`. These class names become the generated frontend type names.
2. **Migration**: import the new models in `backend/migrations/env.py`, then `uv run python -m alembic revision --autogenerate -m "add orders"`. Read the generated file before trusting it, and keep the numbering (`000N_add_orders.py`). Migrations run automatically at startup; never edit an applied one, add a new one instead.
3. **Service**: `backend/app/orders/service.py` holds plain functions that take a `Session` and run SQLModel `select()` queries. All data access and business logic goes here. Data that belongs to a user takes a `user_id` and filters by owner in every function (see `app/dashboards/service.py`).
   **Dataset** (to make it explorable): `backend/app/orders/dataset.py` declares the dimensions and measures people may chart, and `app/analytics/registry.py` lists it. Copy `app/items/dataset.py`. The widget builder and the assistant can then use it; nothing else is needed.
4. **Charts** (optional): `backend/app/orders/charts.py` holds functions that take a `Session` and return a Plotly `Figure` (use `plotly.express` + pandas).
5. **Router**: in `backend/app/orders/router.py`, keep endpoints thin, return charts with `figure_response(fig)`, and include the router in `app/main.py` with `dependencies=signed_in`. An endpoint that needs to know whose data it is takes `user: CurrentUser` (`app/auth/deps.py`). **Login is bypassed for the demo**: a request with no session acts as a built-in demo user, so `CurrentUser` is always present. Per-user scoping still applies, so keep filtering by `user_id` in services.
   The endpoint **function name becomes the frontend function name** (`list_orders` → `listOrdersOptions`), so it must be unique app-wide.
6. **Test**: add `backend/tests/test_orders.py` and run `uv run pytest`. Tests get a fresh SQLite file per test and migrations run for them, so seeded rows are present. The `client` fixture is signed in as "alice"; `make_client("bob")` gives a second user (`tests/conftest.py`).
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
- Store JSON (like a `WidgetSpec`) in a `Text` column and validate it with its pydantic model on the way in and out; `Text` works on both SQLite and HANA.
- A POST that only reads (like `preview_widget`) is used from the frontend with `useQuery` and the SDK function (see `previewOptions` in `src/lib/widgets.ts`); its generated mutation would make every query on screen refetch.
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
| backend | `uv run python -m app.auth.create_user <name>` | Create a user, or reset their password |
| backend | `uv run python -m evals.charting` | Which charts the real model picks (uses the OpenAI key) |
| frontend | `npm run dev` | UI on :5173 |
| frontend | `npm run gen:api` | Regenerate the API client from the backend |
| frontend | `npm run build` / `npm run lint` | Type-check + build, lint |

If Windows App Control blocks `.venv/Scripts/*.exe` (`os error 4551`, or a `uv trampoline`
error), run the module instead: `uv run python -m fastapi dev app/main.py`, `uv run python -m pytest`.

## Analytics, dashboards and the assistant

[DEV.md](DEV.md) is the developer-facing explanation of this section; keep it in step when this changes.

Everything chart-shaped shares one **`WidgetSpec`** (`app/analytics/spec.py`): dataset, dimensions (with an optional time grain), measures, filters, and a chart type. It never contains SQL.

- `app/analytics/query.py` turns a spec into a SQLAlchemy `select()` using only registered fields. `time_bucket` is the one place with per-dialect SQL (SQLite vs HANA); check both if you touch it.
- `app/analytics/recommend.py` picks the best chart for a result's shape ("Show Me" rules) and says whether a requested chart can be drawn. `app/assistant/skills/charting.md` tells the model the same rules; keep the two in step.
- `app/analytics/render.py` draws each chart type with `plotly.express`, using a fixed colorblind-checked palette. `PlotlyChart.tsx` swaps each color for its dark-mode step, so add colors in both places or not at all.
- Dashboards (`app/dashboards/`) store widgets as a spec plus a grid position. `widget_data` re-runs the spec every time, so pinned charts stay current.

The assistant (Explore page, and the header's side panel) runs a **pydantic-ai** agent against OpenAI through the backend; the browser never sees the key.

- `app/assistant/agent.py`: model, instructions and `TOOLSETS`. Tools live with their feature: `app/analytics/tools.py` (describe, distinct values, run a query, make a chart) and `app/dashboards/tools.py` (list, add a chart). To add an ability, write a tool in `app/<feature>/tools.py` that calls that feature's `service.py`, and add its toolset to `TOOLSETS`.
- `app/assistant/prompts.py` (`SYSTEM_PROMPT`) and `skills/charting.md` are the instructions; the dataset catalog and today's date are appended per run.
- `app/assistant/router.py`: `POST /api/assistant/chat` streams the Vercel AI SDK protocol (text, tool calls and results). Threads are saved server-side (`chat_threads.messages`); the browser's copy of the history is ignored except for its newest user message.
- Tool errors: raise `ModelRetry("what was wrong")` so the model can fix its call. Tools open their own `Session(ctx.deps.engine)` and commit writes themselves.
- `frontend/src/lib/assistantChat.ts`: the assistant-ui runtime (`@assistant-ui/ai-sdk`) and the tool result types. `src/components/assistant/ToolUI.tsx` draws tool results in the chat (a `make_chart` result is re-rendered from its spec through `preview_widget`, so the chat shows exactly what gets pinned).
- `frontend/src/components/assistant-ui/`: chat UI generated by `npx assistant-ui@latest add thread`. Edit it like shadcn components. The CLI writes files flat into `src/components/`, so move any new `*.aui.tsx` into `src/components/assistant-ui/elements/`. Tools that should show outside the collapsed "tool calls" group are listed in `messageGroupBy` in `thread.aui.tsx`.
- Do **not** use `@assistant-ui/react-ui`; that package is behind `@assistant-ui/react` and fails to build.
- Tests drive the agent with a scripted pydantic-ai `FunctionModel` (`tests/test_assistant.py`), so they never call OpenAI.

Config lives in `backend/.env`: `OPENAI_API_KEY` (required), `OPENAI_MODEL`, `OPENAI_BASE_URL` for Azure or another OpenAI-compatible gateway, and `SECRET_KEY` for the session cookie.
