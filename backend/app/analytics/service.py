"""Run a widget spec: query, pick the chart, draw it.

The builder's preview, saved dashboard widgets and the assistant's charts all go
through `run_widget`, so a pinned chart looks exactly like the one in the chat.
"""

import json
from datetime import date

from sqlmodel import Session

from app.analytics.query import run_query
from app.analytics.recommend import recommend, shape_of
from app.analytics.registry import get_dataset
from app.analytics.render import column_label, default_title, render
from app.analytics.spec import ColumnInfo, WidgetResult, WidgetSpec
from app.charts import figure_response


def run_widget(session: Session, spec: WidgetSpec, today: date | None = None) -> WidgetResult:
    ds = get_dataset(spec.query.dataset)
    result = run_query(session, spec.query, today)
    df = result.df
    shape = shape_of(spec.query, df, ds)
    rec = recommend(spec.chart.type, shape)

    # Draw what was asked for when possible; otherwise the recommendation
    chart_type = spec.chart.type if rec.feasible else rec.best
    if df.empty:
        chart_type = "table"
    fig = render(chart_type, spec.chart, spec.query, df, ds, shape)

    columns = [
        ColumnInfo(
            name=name,
            label=column_label(ds, spec.query, name),
            kind="measure" if name in spec.query.measures else ds.dimensions[name].kind,
        )
        for name in df.columns
    ]
    return WidgetResult(
        title=spec.chart.title or default_title(ds, spec.query),
        chart_type=chart_type,
        figure=figure_response(fig) if fig is not None else None,
        columns=columns,
        rows=json.loads(df.to_json(orient="records", date_format="iso")),
        row_count=len(df),
        truncated=result.truncated,
        recommendation=rec,
    )
