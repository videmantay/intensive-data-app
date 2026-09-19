"""Assistant tools for exploring data. They call the same code as the widget builder.

The model never writes SQL: it fills in a `QuerySpec`, which only accepts registered
fields. A bad spec raises `ModelRetry` with the reason, so the model can fix it.
"""

from typing import Any

from pydantic import BaseModel
from pydantic_ai import FunctionToolset, ModelRetry, RunContext
from sqlmodel import Session

from app.analytics import query as analytics_query
from app.analytics.datasets import SpecError
from app.analytics.registry import get_dataset
from app.analytics.service import run_widget
from app.analytics.spec import ChartSpec, ChartType, QuerySpec, WidgetSpec
from app.assistant.deps import AssistantDeps

toolset: FunctionToolset[AssistantDeps] = FunctionToolset(max_retries=3)

MAX_ROWS_FOR_MODEL = 50


class QueryAnswer(BaseModel):
    columns: list[str]
    rows: list[dict[str, Any]]
    row_count: int
    truncated: bool


class ChartResult(BaseModel):
    spec: WidgetSpec  # what the chat shows and what gets pinned to a dashboard
    title: str
    chart_type: ChartType
    user_requested: ChartType | None
    requested_feasible: bool
    requested_note: str
    recommended: ChartType
    recommended_reason: str
    row_count: int
    preview_rows: list[dict[str, Any]]


@toolset.tool
def describe_dataset(ctx: RunContext[AssistantDeps], dataset: str) -> dict[str, Any]:
    """List a dataset's fields, with example values for each categorical field."""
    try:
        ds = get_dataset(dataset)
        with Session(ctx.deps.engine) as session:
            examples = {
                name: analytics_query.distinct_values(session, dataset, name, limit=12)
                for name, dim in ds.dimensions.items()
                if dim.kind == "categorical"
            }
    except SpecError as exc:
        raise ModelRetry(str(exc)) from exc
    return {"dataset": ds.info().model_dump(), "example_values": examples}


@toolset.tool
def distinct_values(ctx: RunContext[AssistantDeps], dataset: str, field: str, search: str = "") -> list[Any]:
    """Exact values of a dimension (optionally containing `search`). Use before filtering on a value the user typed."""
    try:
        with Session(ctx.deps.engine) as session:
            return analytics_query.distinct_values(session, dataset, field, search, limit=50)
    except SpecError as exc:
        raise ModelRetry(str(exc)) from exc


@toolset.tool
def run_query(ctx: RunContext[AssistantDeps], query: QuerySpec) -> QueryAnswer:
    """Fetch rows to answer in words (a single number, a short list). Returns at most 50 rows."""
    try:
        with Session(ctx.deps.engine) as session:
            result = analytics_query.run_query(session, query, ctx.deps.today)
    except SpecError as exc:
        raise ModelRetry(str(exc)) from exc
    df = result.df
    rows = df.head(MAX_ROWS_FOR_MODEL).to_dict(orient="records")
    rows = [{k: (v.isoformat() if hasattr(v, "isoformat") else v) for k, v in row.items()} for row in rows]
    return QueryAnswer(
        columns=list(df.columns),
        rows=rows,
        row_count=len(df),
        truncated=result.truncated or len(df) > MAX_ROWS_FOR_MODEL,
    )


@toolset.tool
def make_chart(
    ctx: RunContext[AssistantDeps],
    query: QuerySpec,
    chart_type: ChartType | None = None,
    title: str = "",
) -> ChartResult:
    """Show the user a chart of `query`; it appears in the chat with an "Add to dashboard" button.

    Leave `chart_type` empty to get the chart that suits the data best. Set it only when
    the user asked for a specific type; if that type can't show the data, the recommended
    one is drawn instead and `requested_note` says why.
    """
    requested = chart_type or "table"
    try:
        with Session(ctx.deps.engine) as session:
            result = run_widget(
                session, WidgetSpec(query=query, chart=ChartSpec(type=requested, title=title)), ctx.deps.today
            )
    except SpecError as exc:
        raise ModelRetry(str(exc)) from exc

    rec = result.recommendation
    drawn = result.chart_type if chart_type else rec.best
    return ChartResult(
        spec=WidgetSpec(query=query, chart=ChartSpec(type=drawn, title=title)),
        title=result.title,
        chart_type=drawn,
        user_requested=chart_type,
        requested_feasible=rec.feasible if chart_type else True,
        requested_note=rec.requested_note if chart_type else "",
        recommended=rec.best,
        recommended_reason=rec.reason,
        row_count=result.row_count,
        preview_rows=result.rows[:20],
    )
