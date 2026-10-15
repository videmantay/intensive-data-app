---
name: add-dataset
description: Make a FieldOps table explorable in the widget builder and the assistant (Explore) by registering it as an analytics dataset. Use when asked to "make X chartable", "let the assistant answer questions about X", "add X to Explore/dashboards", or when a new feature's data should be queryable with charts.
---

# Register a dataset for charts and the assistant

The widget builder, dashboards and the assistant only query what's registered in
`backend/app/analytics/registry.py`. A dataset maps friendly field names to
SQLAlchemy columns; the assistant never writes SQL, so anything not listed here
is invisible to it.

## Steps

1. **Read first**: the feature's `models.py`, `backend/app/items/dataset.py` (the
   example to copy) and `backend/app/analytics/datasets.py` (the `Dataset`,
   `Dimension`, `Measure` classes).

2. **Create `backend/app/<feature>/dataset.py`**, one `Dataset` constant:
   - `name`: short, lowercase, plural (`shipments`). The assistant sees it.
   - `description`: one sentence saying what one row is ("One row per shipment...").
     The assistant reads it to decide which dataset answers a question.
   - `table`: the SQLModel table class. For fields from another table, see "Joins" below.
   - **Dimensions** (group and filter by). Pick the kind carefully; it drives the chart rules:
     - `categorical`: a small-ish set of labels (category, status, person, site).
     - `temporal`: a TIMESTAMP/DATE column. Allows `grain` (day/week/month...) and relative-date filters.
     - `numeric`: a raw number per row (for histograms and box plots of the raw values).
     - `text`: free text you'd only search with `contains`.
     Skip ids, foreign keys and secrets (password hashes, tokens). Only list what a user should be able to see.
   - **Measures** (aggregates), each a SQLAlchemy expression: `func.sum(Model.qty)`,
     `func.count(Model.id)`, `func.avg(...)`, `func.count(func.distinct(Model.user_id))`.
     Name them for what they mean (`total_shipped`, `shipment_count`), not the SQL.
   - Labels are what users see on axes; write them in plain words, sentence case.
   - Add a `description` wherever a field name isn't self-explanatory.

3. **Register it**: import the constant in `backend/app/analytics/registry.py` and add
   it to the `DATASETS` list.

4. **Test** in `backend/tests/test_<feature>.py`, using the `client` fixture:
   - `GET /api/analytics/datasets` lists it.
   - `POST /api/analytics/preview` with one dimension and one measure returns the rows you
     expect from the seed data (compute the expected numbers by hand).
   - If it has a temporal dimension: a `grain: "week"` query and a `relative` filter.
   - A per-user dataset (rows owned by a user) must not leak other users' rows; see below.

5. **Check**: `uv run pytest`, `uv run ruff check .`, then in `frontend/` run
   `npm run gen:api && npm run build`. No frontend change is needed; the builder and
   assistant pick the dataset up from the API.

6. **Tell the assistant about vocabulary** only if users call things by other names
   (e.g. "dispatched" means shipped): put that in the dataset or field `description`,
   not in `prompts.py`.

## Joins

`Dataset.table` can be any selectable. For fields from a related table, pass a join and
use the joined columns in dimensions:

```python
from sqlalchemy import join
from app.items.models import Item
from app.shipments.models import Shipment

SHIPMENTS = Dataset(
    name="shipments",
    label="Shipments",
    description="One row per shipment of an item.",
    table=join(Shipment, Item, Shipment.item_id == Item.id),
    dimensions={
        "shipped_at": Dimension(Shipment.shipped_at, "Shipped", "temporal"),
        "shipped_by": Dimension(Shipment.shipped_by, "Shipped by", "categorical"),
        "item": Dimension(Item.name, "Item", "categorical"),
        "category": Dimension(Item.category, "Category", "categorical"),
    },
    measures={
        "quantity_shipped": Measure(func.sum(Shipment.quantity), "Quantity shipped"),
        "shipment_count": Measure(func.count(Shipment.id), "Shipments"),
    },
)
```

## Per-user data

Datasets are shared by everyone who can sign in. If rows belong to individual users,
don't register the raw table; ask the user how visibility should work first, because
the analytics query layer doesn't filter by owner yet.

## Gotchas

- Use SQLAlchemy expressions only (no raw SQL strings), so SQLite and HANA both work.
- HANA returns SUM/AVG as `Decimal`; `run_query` converts measures to floats already.
- Keep `recommend.py` and `app/assistant/skills/charting.md` unchanged unless you're
  changing chart rules; a new dataset needs neither.
