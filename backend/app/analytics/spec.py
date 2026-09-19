"""The widget spec: what to query and how to draw it.

A `WidgetSpec` is the one thing the agent, the widget builder and saved dashboard
widgets all share. It only names fields registered in a dataset (see registry.py),
so it can be stored, edited and re-run safely; `query.py` turns it into SQLAlchemy.
These class names become the generated frontend type names.
"""

from typing import Any, Literal, get_args

from pydantic import BaseModel, Field

from app.charts import PlotlyFigure

Grain = Literal["day", "week", "month", "quarter", "year"]
FilterOp = Literal["eq", "ne", "in", "not_in", "gt", "gte", "lt", "lte", "between", "contains", "relative"]
ChartType = Literal[
    "bar", "line", "area", "scatter", "histogram", "box", "pie", "donut",
    "heatmap", "radar", "treemap", "funnel", "kpi", "table",
]  # fmt: skip
FieldKind = Literal["categorical", "temporal", "numeric", "text"]

CHART_TYPES: tuple[ChartType, ...] = get_args(ChartType)


class DimensionRef(BaseModel):
    """A dimension to group by. `grain` buckets a temporal field (e.g. by month)."""

    field: str
    grain: Grain | None = None


class Filter(BaseModel):
    """A condition on a dimension; `relative` periods like "last_week" are resolved when the query runs."""

    field: str
    op: FilterOp
    value: str | int | float | bool | list[str | int | float] | None = None


class SortBy(BaseModel):
    """Sort by a dimension or measure in the query."""

    field: str
    desc: bool = True


class QuerySpec(BaseModel):
    """What to fetch. With measures, rows are grouped by the dimensions; without, raw rows are returned."""

    dataset: str
    dimensions: list[DimensionRef] = Field(default_factory=list, max_length=3)
    measures: list[str] = Field(default_factory=list, max_length=8)
    filters: list[Filter] = Field(default_factory=list, max_length=20)
    sort: list[SortBy] = Field(default_factory=list, max_length=3)
    limit: int = Field(default=1000, ge=1, le=5000)


class ChartSpec(BaseModel):
    """How to draw the result. Empty fields are filled from the query (x = first dimension, y = measures)."""

    type: ChartType = "bar"
    title: str = Field(default="", max_length=200)
    x: str | None = None
    y: list[str] = Field(default_factory=list)
    color: str | None = None
    orientation: Literal["v", "h"] | None = None
    stacked: bool = False
    top_n: int | None = Field(default=None, ge=1, le=50)


class WidgetSpec(BaseModel):
    """A query plus how to chart it: everything needed to redraw a widget with fresh data."""

    query: QuerySpec
    chart: ChartSpec = Field(default_factory=ChartSpec)


class Recommendation(BaseModel):
    """Which chart suits the result best, and whether the requested one can be drawn."""

    best: ChartType
    reason: str
    requested: ChartType
    feasible: bool
    requested_note: str = ""
    alternatives: list[ChartType] = Field(default_factory=list)


class ColumnInfo(BaseModel):
    """A column in a widget's result rows."""

    name: str
    label: str
    kind: FieldKind | Literal["measure"]


class WidgetResult(BaseModel):
    """A widget's data and figure. `chart_type` is what was drawn (the recommendation if the request was infeasible)."""

    title: str
    chart_type: ChartType
    figure: PlotlyFigure | None
    columns: list[ColumnInfo]
    rows: list[dict[str, Any]]
    row_count: int
    truncated: bool
    recommendation: Recommendation


class DimensionInfo(BaseModel):
    """A field you can group or filter by."""

    name: str
    label: str
    kind: FieldKind
    description: str = ""


class MeasureInfo(BaseModel):
    """An aggregate you can chart (a sum, count or average)."""

    name: str
    label: str
    description: str = ""


class DatasetInfo(BaseModel):
    """A dataset the builder and the assistant can query."""

    name: str
    label: str
    description: str
    dimensions: list[DimensionInfo]
    measures: list[MeasureInfo]
