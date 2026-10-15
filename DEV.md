# Developer guide: dashboards, datasets and Explore

How charts get from a database table to a dashboard tile, and what you change to make a
new table chartable. For running the app see [README.md](README.md); for the general
"add a feature" recipe see [CLAUDE.md](CLAUDE.md).

## The short version

- **Only registered datasets can be charted.** A dataset is a Python object that names the
  fields people may group by (*dimensions*) and the aggregates they may chart (*measures*).
  Nothing else in the database is reachable from the builder, dashboards or the assistant.
- **Every chart is a `WidgetSpec`**: JSON that names a dataset, some of its fields, filters and
  a chart type. It never contains SQL.
- **The backend turns a spec into a SQLAlchemy query, runs it, and draws a Plotly figure.**
  The frontend only displays the result.

To make a table explorable you write one `dataset.py` and add one line to the registry.
No frontend change is needed.

## How it fits together

```
                          ┌──────────────────── WidgetSpec (JSON, no SQL) ────────────────────┐
Widget builder (UI) ──────┤                                                                    │
Explore / assistant ──────┤   app/analytics/                                                   │
Dashboard tile ───────────┘   query.py      spec → select() using only registered fields      │
                              recommend.py  is the requested chart drawable? what's best?     │
                              render.py     DataFrame → Plotly figure                         │
                                   │                                                          │
                                   ▼                                                          │
                              app/analytics/registry.py  ── DATASETS ── app/items/dataset.py   │
                                                                     └─ app/<feature>/dataset.py
```

### The spec

[`app/analytics/spec.py`](backend/app/analytics/spec.py) defines it. A spec that groups items
by category and sums their quantity:

```json
{
  "query": {
    "dataset": "items",
    "dimensions": [{ "field": "category" }],
    "measures": ["total_quantity"],
    "filters": [{ "field": "created_at", "op": "relative", "value": "last_month" }]
  },
  "chart": { "type": "bar", "title": "Quantity by category" }
}
```

- `dimensions` are what to group by (up to 3). A temporal dimension can take a `grain`
  (`day`, `week`, `month`, `quarter`, `year`).
- `measures` are the aggregates. Without any, the query returns raw rows instead.
- `filters` apply to dimensions. A `relative` filter like `last_month` is resolved **each time
  the query runs**, so a pinned "last month" chart keeps meaning last month.
- `chart` fields left empty are filled in from the query (x = first dimension, y = measures).

### From spec to chart

1. [`query.py`](backend/app/analytics/query.py) looks up every field name in the dataset and
   builds a `select()`. An unknown name raises `SpecError`, which lists the valid names.
   Values are always bound parameters. `time_bucket` is the only per-dialect SQL (SQLite vs
   HANA).
2. [`recommend.py`](backend/app/analytics/recommend.py) looks at the result's shape (how many
   dimensions, what kind, how many rows) and picks the best chart. It also says whether the
   requested chart can be drawn and, if not, draws the recommended one instead.
3. [`render.py`](backend/app/analytics/render.py) draws it with `plotly.express` using a fixed
   colorblind-checked palette.

### Where specs come from

| Source | Code | What it does with the spec |
| --- | --- | --- |
| Widget builder | `frontend/src/components/widgets/WidgetBuilder.tsx` | Point-and-click form; previews via `POST /api/analytics/preview`, saves via `POST /api/dashboards/{id}/widgets` |
| Assistant | `app/analytics/tools.py`, `app/dashboards/tools.py` | The model writes a spec as a tool call (`run_query`, `make_chart`, `add_chart_to_dashboard`) |
| Dashboard tile | `GET /api/widgets/{id}/data` (`widget_data`) | Loads the stored spec and runs it again |

### Dashboards

[`app/dashboards/`](backend/app/dashboards/) stores two tables:

- `Dashboard`: name and `owner_id`. Every service function takes a `user_id` and returns
  `None` (so a 404) for someone else's dashboard.
- `Widget`: the spec (JSON in a `Text` column) plus its grid position (`x`, `y`, `w`, `h`).

Widgets store the spec, **not the data or the figure**. Opening a dashboard runs every tile's
spec again, so tiles always show current data. If a dataset field is later renamed or removed,
tiles that use it fail with a `SpecError` naming the field. Keep field names stable.

A user with no dashboards gets "My dashboard" with one default tile (`ensure_dashboard`).

On the frontend, `routes/index.tsx` is the dashboard page, `components/dashboard/DashboardGrid.tsx`
lays out the tiles (react-grid-layout), and `components/widgets/WidgetView.tsx` draws a result
as a chart or a table.

## Making a table explorable

The table needs a SQLModel model (and a migration, if it's new) first. A table that exists only
in the database can't be registered.

### 1. Describe it: `backend/app/<feature>/dataset.py`

Copy [`app/items/dataset.py`](backend/app/items/dataset.py):

```python
from sqlalchemy import func

from app.analytics.datasets import Dataset, Dimension, Measure
from app.orders.models import Order

ORDERS = Dataset(
    name="orders",                      # used in specs; the assistant sees it
    label="Orders",                     # shown in the builder
    description="One row per customer order, with its status and value.",
    table=Order,
    dimensions={
        "status": Dimension(Order.status, "Status", "categorical"),
        "region": Dimension(Order.region, "Region", "categorical"),
        "created_at": Dimension(Order.created_at, "Ordered", "temporal", "When the order was placed"),
        "value": Dimension(Order.value, "Order value", "numeric", "Value of a single order"),
    },
    measures={
        "order_count": Measure(func.count(Order.id), "Orders"),
        "total_value": Measure(func.sum(Order.value), "Total value", "Sum of order value"),
        "avg_value": Measure(func.avg(Order.value), "Average value"),
    },
)
```

Choosing fields:

| Dimension kind | Use for | Enables |
| --- | --- | --- |
| `categorical` | A small set of labels: status, category, site, person | Bars, pies, colors by group |
| `temporal` | A `TIMESTAMP` / `DATE` column | Time grains, relative-date filters, line charts |
| `numeric` | A raw number per row | Histograms and box plots of the raw values |
| `text` | Free text | `contains` filters only |

- Leave out ids, foreign keys and anything sensitive. If it isn't listed, nobody can query it.
- Measures are any SQLAlchemy aggregate: `func.sum`, `func.count`, `func.avg`,
  `func.count(func.distinct(...))`. Name them for what they mean (`total_value`), not the SQL.
- Write `description`s in plain words. The assistant reads them to decide which dataset and
  field answer a question, so put synonyms there ("also called dispatched").
- For fields from a related table, set `table` to a `join(...)` and use the joined columns.
  See `.claude/skills/add-dataset/SKILL.md` for an example.

### 2. Register it: [`app/analytics/registry.py`](backend/app/analytics/registry.py)

```python
from app.items.dataset import ITEMS
from app.orders.dataset import ORDERS

DATASETS: dict[str, Dataset] = {d.name: d for d in [ITEMS, ORDERS]}
```

That's all. The registry feeds:

- `GET /api/analytics/datasets` (the builder's dataset picker),
- `catalog()`, the text appended to the assistant's instructions on every run,
- `query.py`, which rejects any field that isn't in it.

### 3. Test it

Add a test to `backend/tests/test_<feature>.py` using the `client` fixture:

- `GET /api/analytics/datasets` includes the new dataset.
- `POST /api/analytics/preview` with one dimension and one measure returns the numbers you
  expect from the seed data (work them out by hand).
- With a temporal dimension: a `"grain": "week"` query and a `relative` filter.

Then:

```sh
cd backend  && uv run pytest && uv run ruff check .
cd frontend && npm run gen:api && npm run build
```

## Caveats

- **Datasets aren't scoped per user.** Everyone sees all rows of a registered dataset. Dashboards
  are per user, but the data behind them isn't filtered by owner. If a table's rows belong to
  individual users, don't register it as is: `query.py` would need an owner filter first.
- **Don't touch the chart rules for a new dataset.** `recommend.py` and
  `app/assistant/skills/charting.md` describe the same rules and must change together. A new
  dataset needs neither.
- **HANA hasn't been tested against a real instance.** Use SQLAlchemy expressions only (no raw
  SQL) in dimensions and measures so both dialects work.
