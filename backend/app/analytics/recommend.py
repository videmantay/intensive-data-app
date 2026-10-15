"""Pick the chart that suits a result, like Tableau's "Show Me".

The rules look only at the result's shape: how many dimensions and measures, their
kinds, how many distinct values, and whether anything is negative. They mirror the
table in `app/assistant/skills/charting.md`; keep the two in step.
"""

from dataclasses import dataclass

import pandas as pd

from app.analytics.datasets import Dataset
from app.analytics.spec import ChartType, FieldKind, QuerySpec, Recommendation

MAX_BARS = 15  # beyond this, bars show the top 15 and fold the rest into "Other"
MAX_SERIES = 7  # colors per chart; beyond this, fold into "Other" or use a heatmap
MAX_SLICES = 7

# Order in which to offer alternatives
PREFERENCE: tuple[ChartType, ...] = (
    "bar", "line", "area", "heatmap", "scatter", "histogram", "box",
    "donut", "pie", "treemap", "radar", "funnel", "kpi", "table",
)  # fmt: skip


@dataclass(frozen=True)
class Dim:
    name: str
    label: str
    kind: FieldKind  # a dimension with a grain counts as temporal
    cardinality: int


@dataclass(frozen=True)
class Shape:
    dims: list[Dim]
    measures: list[str]
    rows: int
    negatives: bool

    @property
    def categorical(self) -> list[Dim]:
        return [d for d in self.dims if d.kind in ("categorical", "text")]

    @property
    def temporal(self) -> list[Dim]:
        return [d for d in self.dims if d.kind == "temporal"]

    @property
    def numeric(self) -> list[Dim]:
        return [d for d in self.dims if d.kind == "numeric"]


def shape_of(query: QuerySpec, df: pd.DataFrame, ds: Dataset) -> Shape:
    dims = [
        Dim(r.field, ds.label_of(r.field), ds.dimensions[r.field].kind, int(df[r.field].nunique()))
        for r in query.dimensions
    ]
    negatives = any(bool((df[m] < 0).any()) for m in query.measures)
    return Shape(dims=dims, measures=list(query.measures), rows=len(df), negatives=negatives)


def infeasible_reason(chart: ChartType, s: Shape) -> str | None:
    """Why `chart` can't show this result, or None if it can."""
    nd, nm = len(s.dims), len(s.measures)
    numeric_values = len(s.numeric) + nm
    if chart == "table":
        return None
    if chart == "kpi":
        return None if nd == 0 and 1 <= nm <= 4 else "a KPI shows up to 4 totals with no grouping"
    if chart == "bar":
        if nm == 0 or not 1 <= nd <= 2:
            return "a bar chart needs one or two dimensions and a measure"
        return "with two dimensions a bar chart shows one measure" if nd == 2 and nm > 1 else None
    if chart in ("line", "area"):
        if nm == 0 or not 1 <= nd <= 2:
            return f"a {chart} chart needs a time axis and a measure"
        if not (s.temporal or s.numeric):
            return f"a {chart} chart needs a time (or other ordered) axis, and this query has none"
        return f"with two dimensions a {chart} chart shows one measure" if nd == 2 and nm > 1 else None
    if chart == "scatter":
        return None if numeric_values >= 2 else "a scatter plot needs two numeric values per point"
    if chart == "histogram":
        if (nm == 0 and s.numeric) or (nm == 1 and nd >= 1):
            return None
        return "a histogram needs a numeric field with many values"
    if chart == "box":
        return (
            None if nm == 0 and s.numeric else "a box plot needs raw numeric values (a numeric dimension, no measures)"
        )
    if chart in ("pie", "donut"):
        if nd != 1 or nm != 1:
            return f"a {chart} chart needs exactly one dimension and one measure"
        if s.negatives:
            return f"a {chart} chart can't show negative values"
        if s.dims[0].cardinality > 12:
            return f"{s.dims[0].cardinality} slices are too many to compare in a {chart} chart"
        return None
    if chart == "heatmap":
        return None if nd == 2 and nm == 1 else "a heatmap needs two dimensions and one measure"
    if chart == "radar":
        if nd == 1 and nm == 1 and 3 <= s.dims[0].cardinality <= 12:
            return None
        if nd == 1 and 3 <= nm <= 8 and s.dims[0].cardinality <= 5:
            return None
        return "a radar needs one dimension with 3-12 values, or 3-8 measures across up to 5 entities"
    if chart == "treemap":
        if nm != 1 or not 1 <= nd <= 2 or len(s.categorical) != nd:
            return "a treemap needs one or two categorical dimensions and one measure"
        return "a treemap can't show negative values" if s.negatives else None
    if chart == "funnel":
        return None if nd == 1 and nm == 1 else "a funnel needs one dimension (the stages) and one measure"
    return f"unknown chart type {chart!r}"


def best_chart(s: Shape) -> tuple[ChartType, str]:
    """The chart that reads best for this shape, and why (one sentence fragment)."""
    nd, nm = len(s.dims), len(s.measures)
    if s.rows == 0:
        return "table", "no rows matched, so there is nothing to plot"
    if nd == 0:
        return ("kpi", "it's a single total") if nm <= 4 else ("table", "there are too many totals for KPI tiles")
    if nm == 0:
        if nd == 1 and s.numeric:
            return "histogram", "it shows how a single numeric field is distributed"
        if nd == 2 and len(s.numeric) == 1 and len(s.categorical) == 1:
            return "box", "it compares the spread of values across groups"
        if len(s.numeric) >= 2:
            return "scatter", "it shows how two numeric fields relate"
        return "table", "raw rows without a measure read best as a table"

    if nd == 1:
        d = s.dims[0]
        if d.kind == "temporal":
            return "line", "the axis is time, and a line shows the trend"
        if nm == 2 and d.cardinality > 5:
            return "scatter", "it relates two measures across many entities"
        if nm > 1:
            return "bar", "grouped bars compare a few measures side by side on one axis"
        if d.cardinality > MAX_BARS:
            return (
                "bar",
                f"with {d.cardinality} values, the top {MAX_BARS} as sorted bars (the rest as Other) stay readable",
            )
        return "bar", "sorted bars make comparing and ranking values easy"

    if nd == 2 and nm == 1:
        if s.temporal and s.categorical:
            series = s.categorical[0].cardinality
            if series <= MAX_SERIES:
                return "line", "one line per group shows how each trend changes over time"
            return "heatmap", f"{series} groups are too many lines to tell apart"
        if min(d.cardinality for d in s.dims) <= MAX_SERIES:
            return "bar", "stacked bars show each group's total and its breakdown"
        return "heatmap", "both dimensions have many values, so a grid of colored cells reads better"

    return "table", "this many dimensions and measures read best as a table"


def recommend(requested: ChartType, s: Shape) -> Recommendation:
    best, reason = best_chart(s)
    note = infeasible_reason(requested, s) or ""
    alternatives = [c for c in PREFERENCE if c not in (best, requested) and infeasible_reason(c, s) is None]
    return Recommendation(
        best=best,
        reason=reason,
        requested=requested,
        feasible=not note,
        requested_note=note,
        alternatives=alternatives[:4],
    )
