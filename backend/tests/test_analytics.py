from datetime import date, datetime

import pytest
from sqlmodel import Session

from app.analytics.datasets import SpecError
from app.analytics.query import resolve_relative, run_query
from app.analytics.recommend import PREFERENCE
from app.analytics.service import run_widget
from app.analytics.spec import CHART_TYPES, QuerySpec, WidgetSpec
from app.items.models import Item

TODAY = date(2026, 9, 19)  # a Saturday


def preview(client, query: dict, chart: dict | None = None):
    res = client.post("/api/analytics/preview", json={"query": {"dataset": "items", **query}, "chart": chart or {}})
    assert res.status_code == 200, res.text
    return res.json()


QTY_BY_CATEGORY = {"dimensions": [{"field": "category"}], "measures": ["total_quantity"]}


def test_datasets_catalog(client, anon_client):
    [items] = client.get("/api/analytics/datasets").json()
    assert items["name"] == "items"
    assert {d["name"]: d["kind"] for d in items["dimensions"]}["created_at"] == "temporal"
    assert "total_quantity" in [m["name"] for m in items["measures"]]
    # Login is bypassed for the demo, so this works without signing in too
    assert anon_client.get("/api/analytics/datasets").status_code == 200


def test_bar_by_category_is_sorted_and_recommended(client):
    result = preview(client, QTY_BY_CATEGORY)
    assert result["chart_type"] == "bar"
    assert result["title"] == "Total quantity by category"
    assert result["rows"][0] == {"category": "Hardware", "total_quantity": 4150}
    assert [r["total_quantity"] for r in result["rows"]] == sorted(
        (r["total_quantity"] for r in result["rows"]), reverse=True
    )
    rec = result["recommendation"]
    assert rec["best"] == "bar" and rec["feasible"]
    assert result["figure"]["data"][0]["type"] == "bar"


def test_requested_radar_is_drawn_but_bar_recommended(client):
    result = preview(client, QTY_BY_CATEGORY, {"type": "radar"})
    assert result["chart_type"] == "radar"
    assert result["figure"]["data"][0]["type"] == "scatterpolar"
    assert result["recommendation"]["feasible"]
    assert result["recommendation"]["best"] == "bar"


def test_infeasible_request_falls_back_to_recommendation(client):
    result = preview(client, QTY_BY_CATEGORY, {"type": "line"})
    assert result["chart_type"] == "bar"
    rec = result["recommendation"]
    assert not rec["feasible"]
    assert "time" in rec["requested_note"]


def test_kpi_and_histogram(client):
    kpi = preview(client, {"measures": ["total_quantity", "item_count"]}, {"type": "kpi"})
    assert kpi["chart_type"] == "kpi"
    assert kpi["rows"] == [{"total_quantity": 5149, "item_count": 8}]
    assert [t["type"] for t in kpi["figure"]["data"]] == ["indicator", "indicator"]

    hist = preview(client, {"dimensions": [{"field": "quantity"}]})
    assert hist["recommendation"]["best"] == "histogram"
    assert hist["row_count"] == 8  # raw rows, not grouped


@pytest.mark.parametrize(
    "filter_, expected",
    [
        ({"field": "category", "op": "in", "value": ["Safety", "Electrical"]}, {"Safety", "Electrical"}),
        ({"field": "category", "op": "ne", "value": "Hardware"}, {"Electrical", "Safety", "Consumables"}),
        ({"field": "name", "op": "contains", "value": "HARD"}, {"Safety"}),  # case-insensitive
        ({"field": "quantity", "op": "gte", "value": 1000}, {"Hardware"}),
        ({"field": "quantity", "op": "between", "value": [100, 400]}, {"Safety", "Consumables"}),
    ],
)
def test_filters(client, filter_, expected):
    result = preview(client, {**QTY_BY_CATEGORY, "filters": [filter_]})
    assert {r["category"] for r in result["rows"]} == expected


@pytest.mark.parametrize(
    "query, message",
    [
        ({"dimensions": [{"field": "colour"}], "measures": ["item_count"]}, "no dimension 'colour'"),
        ({"dimensions": [{"field": "total_quantity"}]}, "that's a measure"),
        ({"dimensions": [{"field": "category", "grain": "month"}], "measures": ["item_count"]}, "grain"),
        ({"measures": ["item_count"], "filters": [{"field": "category", "op": "relative", "value": "x"}]}, "temporal"),
        ({"measures": ["item_count"], "filters": [{"field": "created_at", "op": "relative", "value": "soon"}]}, "soon"),
        ({"measures": ["item_count"], "sort": [{"field": "name"}]}, "sort"),
        ({}, "at least one"),
    ],
)
def test_bad_specs_explain_themselves(client, query, message):
    res = client.post("/api/analytics/preview", json={"query": {"dataset": "items", **query}})
    assert res.status_code == 422
    assert message in res.json()["detail"]


@pytest.mark.parametrize(
    "period, start, end",
    [
        ("today", date(2026, 9, 19), date(2026, 9, 20)),
        ("last_week", date(2026, 9, 7), date(2026, 9, 14)),
        ("this_week", date(2026, 9, 14), date(2026, 9, 21)),
        ("this_month", date(2026, 9, 1), date(2026, 10, 1)),
        ("last_month", date(2026, 8, 1), date(2026, 9, 1)),
        ("last_quarter", date(2026, 4, 1), date(2026, 7, 1)),
        ("ytd", date(2026, 1, 1), date(2026, 9, 20)),
        ("last_n_days:7", date(2026, 9, 13), date(2026, 9, 20)),
        ("last_n_months:3", date(2026, 7, 1), date(2026, 9, 20)),
    ],
)
def test_relative_periods(period, start, end):
    assert resolve_relative(period, TODAY) == (
        datetime.combine(start, datetime.min.time()),
        datetime.combine(end, datetime.min.time()),
    )


def test_last_month_wraps_the_year():
    assert resolve_relative("last_month", date(2026, 1, 15))[0] == datetime(2025, 12, 1)


def _add_dated_items(client):
    with Session(client.app.state.engine) as session:
        for when, qty in [
            (datetime(2026, 9, 8, 10), 5),  # Tue, last week
            (datetime(2026, 9, 13, 23), 7),  # Sun, last week
            (datetime(2026, 9, 15, 9), 11),  # this week
            (datetime(2026, 7, 2, 12), 13),  # July
        ]:
            session.add(Item(name=f"dated {qty}", category="Dated", quantity=qty, created_at=when))
        session.commit()


def test_time_buckets_and_relative_filter(client):
    _add_dated_items(client)
    with Session(client.app.state.engine) as session:
        by_week = QuerySpec(
            dataset="items",
            dimensions=[{"field": "created_at", "grain": "week"}],
            measures=["total_quantity"],
            filters=[{"field": "category", "op": "eq", "value": "Dated"}],
        )
        df = run_query(session, by_week, TODAY).df
        assert [(d.date().isoformat(), q) for d, q in zip(df["created_at"], df["total_quantity"], strict=True)] == [
            ("2026-06-29", 13),
            ("2026-09-07", 12),
            ("2026-09-14", 11),
        ]

        by_month = QuerySpec(**{**by_week.model_dump(), "dimensions": [{"field": "created_at", "grain": "month"}]})
        months = run_query(session, by_month, TODAY).df["created_at"].dt.strftime("%Y-%m-%d").tolist()
        assert months == ["2026-07-01", "2026-09-01"]

        last_week = QuerySpec(
            dataset="items",
            measures=["total_quantity"],
            filters=[{"field": "created_at", "op": "relative", "value": "last_week"}],
        )
        assert run_query(session, last_week, TODAY).df["total_quantity"].tolist() == [12]


def test_line_over_time_is_recommended(client):
    _add_dated_items(client)
    with Session(client.app.state.engine) as session:
        spec = WidgetSpec(
            query={
                "dataset": "items",
                "dimensions": [{"field": "created_at", "grain": "day"}],
                "measures": ["total_quantity"],
                "filters": [{"field": "category", "op": "eq", "value": "Dated"}],
            },
            chart={"type": "line"},
        )
        result = run_widget(session, spec, TODAY)
    assert result.chart_type == "line"
    assert result.recommendation.best == "line"


def test_many_categories_fold_into_other(client):
    with Session(client.app.state.engine) as session:
        for i in range(20):
            session.add(Item(name=f"thing {i}", category=f"Cat {i:02d}", quantity=i + 1))
        session.commit()
    result = preview(client, QTY_BY_CATEGORY)
    bars = result["figure"]["data"][0]
    labels = bars["y"] if bars.get("orientation") == "h" else bars["x"]
    assert len(labels) == 16 and "Other" in labels


# One spec per chart type, shaped so that type is feasible
EVERY_CHART = {
    "bar": QTY_BY_CATEGORY,
    "line": {"dimensions": [{"field": "created_at", "grain": "day"}], "measures": ["total_quantity"]},
    "area": {"dimensions": [{"field": "created_at", "grain": "day"}], "measures": ["total_quantity"]},
    "scatter": {"dimensions": [{"field": "category"}], "measures": ["total_quantity", "item_count"]},
    "histogram": {"dimensions": [{"field": "quantity"}]},
    "box": {"dimensions": [{"field": "category"}, {"field": "quantity"}]},
    "pie": QTY_BY_CATEGORY,
    "donut": QTY_BY_CATEGORY,
    "heatmap": {"dimensions": [{"field": "category"}, {"field": "name"}], "measures": ["total_quantity"]},
    "radar": QTY_BY_CATEGORY,
    "treemap": {"dimensions": [{"field": "category"}, {"field": "name"}], "measures": ["total_quantity"]},
    "funnel": QTY_BY_CATEGORY,
    "kpi": {"measures": ["total_quantity"]},
    "table": QTY_BY_CATEGORY,
}


@pytest.mark.parametrize("chart_type", CHART_TYPES)
def test_every_chart_type_renders(client, chart_type):
    result = preview(client, EVERY_CHART[chart_type], {"type": chart_type})
    assert result["recommendation"]["feasible"], result["recommendation"]
    assert result["chart_type"] == chart_type
    assert (result["figure"] is None) == (chart_type == "table")


def test_every_chart_type_has_a_preference():
    assert set(PREFERENCE) == set(CHART_TYPES)


def test_dimension_values(client):
    assert client.get("/api/analytics/datasets/items/values/category").json() == [
        "Consumables",
        "Electrical",
        "Hardware",
        "Safety",
    ]
    assert client.get("/api/analytics/datasets/items/values/category?search=ARD").json() == ["Hardware"]
    assert client.get("/api/analytics/datasets/items/values/nope").status_code == 422


def test_unknown_dataset(client):
    with Session(client.app.state.engine) as session, pytest.raises(SpecError, match="Unknown dataset 'nope'"):
        run_query(session, QuerySpec(dataset="nope", measures=["item_count"]))
