"""Draw a query result as a Plotly figure, one small function per chart type.

Colors follow a fixed categorical order that has been checked for colorblind safety.
`frontend/src/components/PlotlyChart.tsx` swaps each color for its dark-mode step, so
use only the hex values listed here. More than 7 series are folded into "Other"
rather than given new colors.
"""

from collections.abc import Callable
from dataclasses import dataclass

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

from app.analytics.datasets import Dataset
from app.analytics.recommend import MAX_BARS, MAX_SERIES, MAX_SLICES, Shape
from app.analytics.spec import ChartSpec, ChartType, QuerySpec

# Categorical slots, in this order (light-mode steps; PlotlyChart.tsx maps them to dark)
SERIES = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#4a3aa7", "#e34948"]
OTHER = "#898781"  # "Other" and de-emphasized marks
# Sequential blue, light to dark, for magnitude (heatmaps)
SEQUENTIAL = ["#cde2fb", "#9ec5f4", "#6da7ec", "#3987e5", "#256abf", "#184f95", "#0d366b"]


@dataclass
class Plot:
    """The chart spec with blanks filled in from the query."""

    df: pd.DataFrame
    x: str | None
    y: list[str]
    color: str | None
    labels: dict[str, str]
    chart: ChartSpec
    shape: Shape


def column_label(ds: Dataset, query: QuerySpec, name: str) -> str:
    for ref in query.dimensions:
        if ref.field == name and ref.grain:
            return f"{ds.label_of(name)} ({ref.grain})"
    return ds.label_of(name)


def default_title(ds: Dataset, query: QuerySpec) -> str:
    measures = [ds.label_of(m) for m in query.measures]
    dims = [column_label(ds, query, r.field) for r in query.dimensions]
    if measures and dims:
        title = f"{', '.join(measures)} by {' and '.join(dims).lower()}"
    elif measures:
        title = ", ".join(measures)
    else:
        title = f"Distribution of {' and '.join(dims)}"
    periods = [str(f.value).replace("_", " ") for f in query.filters if f.op == "relative"]
    return f"{title} · {', '.join(periods)}" if periods else title


def _fold(df: pd.DataFrame, key: str, value: str, keep: int) -> pd.DataFrame:
    """Keep the `keep` largest `key` groups by total `value`; sum the rest into "Other"."""
    totals = df.groupby(key, sort=False)[value].sum().sort_values(ascending=False)
    if len(totals) <= keep:
        return df
    top = set(totals.index[:keep])
    folded = df.assign(**{key: df[key].where(df[key].isin(top), "Other")})
    others = [c for c in df.columns if c != value]  # callers pass one value column
    return folded.groupby(others, as_index=False, sort=False)[value].sum()


def _color_map(values) -> dict[str, str]:
    """Fixed slot per series, in order of appearance; "Other" is always gray."""
    names = [v for v in dict.fromkeys(values) if v != "Other"]
    mapping = {str(v): SERIES[i % len(SERIES)] for i, v in enumerate(names)}
    mapping["Other"] = OTHER
    return mapping


def _is_categorical(p: Plot, col: str | None) -> bool:
    return col is not None and any(d.name == col and d.kind in ("categorical", "text") for d in p.shape.dims)


def _bar(p: Plot) -> go.Figure:
    df, x, color = p.df, p.x, p.color
    y = p.y
    if len(y) > 1:  # several measures: one bar per measure, side by side
        df = df.melt(id_vars=[x], value_vars=y, var_name="measure", value_name="value")
        df["measure"] = df["measure"].map(p.labels)
        color, y = "measure", ["value"]
    value = y[0]
    if color and _is_categorical(p, color):
        df = _fold(df, color, value, MAX_SERIES)
    if _is_categorical(p, x) and not color:
        keep = p.chart.top_n or (MAX_BARS if df[x].nunique() > MAX_BARS else None)
        if keep:
            df = _fold(df, x, value, keep)
        df = df.sort_values(value, ascending=False)
    horizontal = p.chart.orientation == "h" or (
        p.chart.orientation is None
        and _is_categorical(p, x)
        and (df[x].nunique() > 8 or df[x].astype(str).str.len().max() > 14)
    )
    kwargs = {"labels": {**p.labels, "value": ""}, "barmode": "stack" if p.chart.stacked else "group"}
    if color:
        kwargs |= {"color": color, "color_discrete_map": _color_map(df[color])}
    else:
        kwargs |= {"color_discrete_sequence": SERIES}
    if horizontal:
        fig = px.bar(df, x=value, y=x, orientation="h", **kwargs)
        fig.update_yaxes(autorange="reversed", showgrid=False)  # largest on top
        fig.update_xaxes(showgrid=True)
    else:
        fig = px.bar(df, x=x, y=value, **kwargs)
    return fig


def _line(p: Plot, area: bool = False) -> go.Figure:
    df, color = p.df, p.color
    draw = px.area if area else px.line
    if color:
        df = _fold(df, color, p.y[0], MAX_SERIES)
        fig = draw(df, x=p.x, y=p.y[0], color=color, color_discrete_map=_color_map(df[color]), labels=p.labels)
    else:
        fig = draw(df, x=p.x, y=p.y, color_discrete_sequence=SERIES, labels={**p.labels, "variable": ""})
        fig.for_each_trace(lambda t: t.update(name=p.labels.get(t.name, t.name)))
    fig.update_traces(line_width=2, mode="lines+markers" if len(df) <= 40 else "lines", marker_size=8)
    return fig


def _numeric_columns(p: Plot) -> list[str]:
    return [d.name for d in p.shape.numeric] + p.shape.measures


def _scatter(p: Plot) -> go.Figure:
    x, y = _numeric_columns(p)[:2]
    label = next((d.name for d in p.shape.categorical), None)
    color = p.color if _is_categorical(p, p.color) and p.shape.measures == [] else None
    fig = px.scatter(
        p.df,
        x=x,
        y=y,
        color=color,
        hover_name=label,
        labels=p.labels,
        color_discrete_sequence=SERIES,
    )
    fig.update_traces(marker={"size": 9, "opacity": 0.85})
    return fig


def _histogram(p: Plot) -> go.Figure:
    value = next(iter(d.name for d in p.shape.numeric), None) or p.shape.measures[0]
    fig = px.histogram(p.df, x=value, labels=p.labels, color_discrete_sequence=SERIES)
    fig.update_yaxes(title_text="Count")
    fig.update_layout(bargap=0.05)
    return fig


def _box(p: Plot) -> go.Figure:
    value = p.shape.numeric[0].name
    group = next((d.name for d in p.shape.categorical), None)
    return px.box(p.df, x=group, y=value, labels=p.labels, color_discrete_sequence=SERIES, points="outliers")


def _pie(p: Plot, hole: float = 0.0) -> go.Figure:
    df = _fold(p.df, p.x, p.y[0], MAX_SLICES).sort_values(p.y[0], ascending=False)
    fig = px.pie(
        df,
        names=p.x,
        values=p.y[0],
        hole=hole,
        labels=p.labels,
        color=p.x,
        color_discrete_map=_color_map(df[p.x]),
    )
    # Big slices label inside, small ones outside; with 7 slices at most they don't collide
    fig.update_traces(sort=False, textinfo="percent+label", textposition="auto", insidetextorientation="horizontal")
    fig.update_layout(margin={"l": 32, "r": 32, "t": 32, "b": 32})
    return fig


def _heatmap(p: Plot) -> go.Figure:
    rows, cols = (p.color, p.x) if p.color else [d.name for d in p.shape.dims][::-1]
    grid = p.df.pivot_table(index=rows, columns=cols, values=p.y[0], aggfunc="sum")
    fig = px.imshow(
        grid,
        aspect="auto",
        color_continuous_scale=SEQUENTIAL,
        labels={"x": p.labels.get(cols, cols), "y": p.labels.get(rows, rows), "color": p.labels.get(p.y[0])},
        text_auto=grid.size <= 60,
    )
    fig.update_xaxes(showgrid=False)
    fig.update_yaxes(showgrid=False)
    return fig


def _radar(p: Plot) -> go.Figure:
    if len(p.y) == 1:  # one measure around the values of one dimension
        fig = px.line_polar(p.df, r=p.y[0], theta=p.x, line_close=True, color_discrete_sequence=SERIES)
    else:  # several measures, one polygon per entity
        df = p.df.melt(id_vars=[p.x], value_vars=p.y, var_name="measure", value_name="value")
        df["measure"] = df["measure"].map(p.labels)
        fig = px.line_polar(
            df, r="value", theta="measure", color=p.x, line_close=True, color_discrete_map=_color_map(df[p.x])
        )
    fig.update_traces(fill="toself", line_width=2, opacity=0.8)
    # First value at 12 o'clock, going clockwise; value ticks up the vertical spoke
    fig.update_layout(
        polar={
            "angularaxis": {"rotation": 90, "direction": "clockwise"},
            "radialaxis": {"angle": 90, "tickangle": 90, "tickfont": {"size": 10}},
        },
        margin={"l": 48, "r": 48, "t": 40, "b": 32},
    )
    return fig


def _treemap(p: Plot) -> go.Figure:
    path = [px.Constant("All"), *[d.name for d in p.shape.categorical]]
    fig = px.treemap(p.df, path=path, values=p.y[0], color_discrete_sequence=SERIES, labels=p.labels)
    fig.update_traces(root_color="rgba(0,0,0,0)", textinfo="label+value")
    return fig


def _funnel(p: Plot) -> go.Figure:
    df = p.df.sort_values(p.y[0], ascending=False)
    return px.funnel(df, x=p.y[0], y=p.x, labels=p.labels, color_discrete_sequence=SERIES)


def _kpi(p: Plot) -> go.Figure:
    fig = go.Figure()
    n = len(p.y)
    for i, name in enumerate(p.y):
        value = float(p.df[name].iloc[0]) if len(p.df) else 0.0
        fig.add_trace(
            go.Indicator(
                mode="number",
                value=value,
                title={"text": p.labels.get(name, name), "font": {"size": 14}},
                number={"valueformat": ",.0f" if value.is_integer() else ",.2f", "font": {"size": 44}},
                domain={"x": [i / n, (i + 1) / n], "y": [0, 1]},
            )
        )
    return fig


_BUILDERS: dict[ChartType, Callable[[Plot], go.Figure]] = {
    "bar": _bar,
    "line": _line,
    "area": lambda p: _line(p, area=True),
    "scatter": _scatter,
    "histogram": _histogram,
    "box": _box,
    "pie": _pie,
    "donut": lambda p: _pie(p, hole=0.55),
    "heatmap": _heatmap,
    "radar": _radar,
    "treemap": _treemap,
    "funnel": _funnel,
    "kpi": _kpi,
}


def render(chart_type: ChartType, chart: ChartSpec, query: QuerySpec, df: pd.DataFrame, ds: Dataset, shape: Shape):
    """The figure for `chart_type`, or None for a table. Assumes the type is feasible."""
    builder = _BUILDERS.get(chart_type)
    if builder is None or df.empty:
        return None
    dims = [r.field for r in query.dimensions]
    x = chart.x if chart.x in dims else (dims[0] if dims else None)
    others = [d for d in dims if d != x]
    color = chart.color if chart.color in others else (others[0] if others else None)
    y = [m for m in chart.y if m in query.measures] or list(query.measures)
    labels = {c: column_label(ds, query, c) for c in df.columns}

    fig = builder(Plot(df=df, x=x, y=y, color=color, labels=labels, chart=chart, shape=shape))
    _style(fig)
    return fig


def _style(fig: go.Figure) -> None:
    # Title lives in the widget/chat header; backgrounds and ink come from the app theme
    fig.update_layout(
        template="plotly_white",
        colorway=SERIES,
        legend={"orientation": "h", "yanchor": "bottom", "y": 1.0, "x": 0, "title_text": ""},
        barcornerradius=4,
        bargap=0.3,
        bargroupgap=0.08,
        hoverlabel={"font_size": 12},
    )
    if fig.layout.margin.l is None:  # builders like _pie and _radar set their own
        fig.update_layout(margin={"l": 8, "r": 8, "t": 32, "b": 8})
    fig.update_xaxes(automargin=True, zeroline=False)
    fig.update_yaxes(automargin=True, zeroline=False)
    if len(fig.data) == 1:
        fig.update_layout(showlegend=False)  # one series: the title names it
