# Library best practices

The official guidance for each library FieldOps uses, picked for the parts we rely on. Each
section starts with how this codebase uses the library, since our own conventions win where
they're stricter.

## Backend

### FastAPI

Routers stay thin: an endpoint parses the request, calls a function in the feature's
`service.py`, and returns. The endpoint function name becomes the generated frontend function
name, so it must be unique app-wide.

- [Bigger applications: multiple files](https://fastapi.tiangolo.com/tutorial/bigger-applications/): one `APIRouter` per feature, included in `main.py`.
- [Dependencies](https://fastapi.tiangolo.com/tutorial/dependencies/): how `DbSession` and `CurrentUser` are injected.
- [Concurrency and async / await](https://fastapi.tiangolo.com/async/): when to write `def` and when `async def`. Most of our endpoints are plain `def` because the database calls block.
- [Testing](https://fastapi.tiangolo.com/tutorial/testing/): `TestClient`, which our `client` fixture wraps.
- [Settings and environment variables](https://fastapi.tiangolo.com/advanced/settings/): the pattern behind `app/config.py`.
- [Deployment concepts](https://fastapi.tiangolo.com/deployment/): workers, restarts, HTTPS.
- [FastAPI best practices (community)](https://github.com/zhanymkanov/fastapi-best-practices): widely used project-structure and convention guide; our feature-folder layout follows the same idea.

### Pydantic, pydantic-settings and pydantic-ai

Models validate everything that crosses a boundary: request bodies, the `WidgetSpec` JSON stored
in `Text` columns, and settings from `backend/.env`.

- [Models](https://docs.pydantic.dev/latest/concepts/models/): defining, validating and dumping models.
- [Validators](https://docs.pydantic.dev/latest/concepts/validators/): field and model validators; prefer them over checking values by hand in services.
- [Performance tips](https://docs.pydantic.dev/latest/concepts/performance/): reuse `TypeAdapter`s, prefer `model_validate_json` for JSON input.
- [Settings management](https://docs.pydantic.dev/latest/concepts/pydantic_settings/): `BaseSettings` and `.env` files.
- [pydantic-ai: agents](https://ai.pydantic.dev/agents/): the assistant in `app/assistant/agent.py`.
- [pydantic-ai: function tools](https://ai.pydantic.dev/tools/): tools live with their feature in `app/<feature>/tools.py`; raise `ModelRetry` for a bad call.
- [pydantic-ai: unit testing](https://ai.pydantic.dev/testing/): `FunctionModel` / `TestModel`, as used in `tests/test_assistant.py`, so tests never call OpenAI.

### SQLModel

One `table=True` model per table, plus separate API shapes (`Base`, `Create`, `Update`,
`Public`). Copy `app/items/models.py`.

- [Multiple models with FastAPI](https://sqlmodel.tiangolo.com/tutorial/fastapi/multiple-models/): why the table model and the API models are separate classes.
- [Session with a dependency](https://sqlmodel.tiangolo.com/tutorial/fastapi/session-with-dependency/): one session per request, which is what `DbSession` gives you.
- [Testing with FastAPI](https://sqlmodel.tiangolo.com/tutorial/fastapi/tests/): overriding the session for tests.

### SQLAlchemy 2.0

All queries are SQLAlchemy `select()` expressions, never SQL strings, so the same code runs on
SQLite and SAP HANA. `app/analytics/query.py` builds queries from a spec this way.

- [Unified tutorial](https://docs.sqlalchemy.org/en/20/tutorial/index.html): the 2.0 style we use throughout (`select()`, `session.execute`).
- [Using SELECT statements](https://docs.sqlalchemy.org/en/20/tutorial/data_select.html): joins, grouping and aggregates, the building blocks of datasets and measures.
- [ORM querying guide](https://docs.sqlalchemy.org/en/20/orm/queryguide/index.html): reference for anything the tutorial doesn't cover.
- [Session basics](https://docs.sqlalchemy.org/en/20/orm/session_basics.html): when to create a session, commit, and close it. Read "When do I construct a Session" before writing a tool or script that opens its own.
- [Performance FAQ](https://docs.sqlalchemy.org/en/20/faq/performance.html): profiling slow queries and the N+1 problem.

### Alembic

Migrations run automatically at startup. Never edit an applied one; add a new one.

- [Tutorial](https://alembic.sqlalchemy.org/en/latest/tutorial.html): revisions, upgrade and downgrade.
- [Auto-generating migrations](https://alembic.sqlalchemy.org/en/latest/autogenerate.html): what autogenerate does and doesn't detect. Read the generated file before trusting it.

### Plotly and pandas

Charts are built in Python with `plotly.express` from a pandas DataFrame and sent to the
browser as JSON.

- [Plotly Express](https://plotly.com/python/plotly-express/): the high-level API used in `render.py` and each feature's `charts.py`.
- [Creating and updating figures](https://plotly.com/python/creating-and-updating-figures/): `update_layout` / `update_traces` for adjusting a figure after Express builds it.
- [pandas user guide](https://pandas.pydata.org/docs/user_guide/index.html): grouping and reshaping data before it's charted.

### Tooling: uv, Ruff, pytest

- [uv: working on projects](https://docs.astral.sh/uv/concepts/projects/): `uv run`, `uv add`, and the lockfile.
- [Ruff](https://docs.astral.sh/ruff/): linting and formatting (`uv run ruff check .` / `uv run ruff format .`).
- [pytest good practices](https://docs.pytest.org/en/stable/explanation/goodpractices.html): test layout and fixtures.

## Frontend

### React

Components fetch and display; they don't compute. Server data lives in TanStack Query, and
simple UI state in `useState` or the URL. No Redux or Zustand.

- [Thinking in React](https://react.dev/learn/thinking-in-react): splitting a page into components and deciding where state lives.
- [Choosing the state structure](https://react.dev/learn/choosing-the-state-structure): keep state minimal; derive the rest while rendering.
- [You might not need an effect](https://react.dev/learn/you-might-not-need-an-effect): the most common React mistake. Most `useEffect`s that set state should be a calculation or a query instead.
- [Rules of React](https://react.dev/reference/rules): purity and the rules of hooks.

### TanStack Query

All server data goes through it, using the options and mutations generated from the API
(`listItemsOptions()`, `createItemMutation()`). After any successful mutation, on-screen data
refetches automatically (`src/lib/queryClient.ts`).

- [Important defaults](https://tanstack.com/query/latest/docs/framework/react/guides/important-defaults): stale time, refetch on focus and retries. Read this first; it explains most "why did it refetch" surprises.
- [Query keys](https://tanstack.com/query/latest/docs/framework/react/guides/query-keys): the generated options build these for you.
- [Query options](https://tanstack.com/query/latest/docs/framework/react/guides/query-options): the `queryOptions` pattern the generated client uses.
- [Query invalidation](https://tanstack.com/query/latest/docs/framework/react/guides/query-invalidation): what our global "refetch after a mutation" does.
- [Practical React Query](https://tkdodo.eu/blog/practical-react-query): the series by the library's maintainer; the de facto best-practices guide.

### TanStack Router

File-based routing: `src/routes/orders.tsx` is the `/orders` page.

- [File-based routing](https://tanstack.com/router/latest/docs/framework/react/routing/file-based-routing): naming conventions for route files.
- [Search params](https://tanstack.com/router/latest/docs/framework/react/guide/search-params): typed URL state, our preferred place for filters and selections that should survive a reload.

### Generated API client (Hey API)

`npm run gen:api` generates types and TanStack Query helpers from the backend's OpenAPI schema.
Never hand-edit `src/api/generated/`.

- [TanStack Query plugin](https://heyapi.dev/openapi-ts/plugins/tanstack-query): what the generated `...Options()` and `...Mutation()` functions are and how to use them.

### AG Grid

Tables use `<DataGrid>` (`src/components/DataGrid.tsx`), which turns on `readOnlyEdit`: the
grid never changes data itself. Handle `onCellEditRequest` by calling an update mutation (see
`routes/items.tsx`).

- [Cell editing](https://www.ag-grid.com/react-data-grid/cell-editing/): how editing starts and stops, and keyboard behavior.
- [Value setters and read-only edit](https://www.ag-grid.com/react-data-grid/value-setters/): the `readOnlyEdit` / `cellEditRequest` pattern we use.
- [Provided cell editors](https://www.ag-grid.com/react-data-grid/provided-cell-editors/): text, large text, select, number, date and checkbox editors.
- [Custom cell editors](https://www.ag-grid.com/react-data-grid/cell-editors/): writing your own, like the icon dropdown on the FORA page.

### UI: shadcn/ui, Tailwind CSS, assistant-ui

- [shadcn/ui](https://ui.shadcn.com/docs): components are copied into `src/components/ui/` and edited like our own code; add more with `npx shadcn@latest add <name>`.
- [Tailwind: styling with utility classes](https://tailwindcss.com/docs/styling-with-utility-classes): the core idea, and how to handle repeated styles.
- [assistant-ui](https://www.assistant-ui.com/docs): the chat UI behind the assistant panel. Use `@assistant-ui/react`, not `@assistant-ui/react-ui`.
