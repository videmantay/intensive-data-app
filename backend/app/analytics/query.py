"""Turn a `QuerySpec` into a SQLAlchemy `select()` and run it into a DataFrame.

Every field is looked up in the dataset registry, so a spec can only reach registered
columns and values are always bound parameters. Bucketing timestamps by week/month is
the one thing SQLite and HANA spell differently; that lives in `time_bucket`.
"""

import operator
import re
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from decimal import Decimal
from typing import Any

import pandas as pd
from sqlalchemy import Integer, Select, and_, cast, func, select
from sqlalchemy.sql.elements import ColumnElement
from sqlmodel import Session

from app.analytics.datasets import Dimension, SpecError
from app.analytics.registry import get_dataset
from app.analytics.spec import Filter, Grain, QuerySpec
from app.db.types import utcnow

RELATIVE_PERIODS = (
    "today", "yesterday", "this_week", "last_week", "this_month", "last_month", "this_quarter",
    "last_quarter", "this_year", "last_year", "ytd", "last_n_days:N", "last_n_weeks:N", "last_n_months:N",
)  # fmt: skip

_COMPARISONS = {
    "eq": operator.eq,
    "ne": operator.ne,
    "gt": operator.gt,
    "gte": operator.ge,
    "lt": operator.lt,
    "lte": operator.le,
}


@dataclass
class QueryResult:
    df: pd.DataFrame
    truncated: bool  # more rows matched than `limit`


def _month_start(d: date, months_back: int = 0) -> date:
    """First day of the month `months_back` months before `d` (negative = later)."""
    m = d.month - 1 - months_back
    return date(d.year + m // 12, m % 12 + 1, 1)


def resolve_relative(period: str, today: date) -> tuple[datetime, datetime]:
    """A relative period as a half-open [start, end) range of naive UTC datetimes."""
    p = period.strip().lower()
    if match := re.fullmatch(r"last_n_(days|weeks|months):(\d{1,4})", p):
        unit, n = match[1], int(match[2])
        if n < 1:
            raise SpecError(f"{period!r}: N must be at least 1")
        if unit == "days":
            start = today - timedelta(days=n - 1)
        elif unit == "weeks":
            start = today - timedelta(days=7 * n - 1)
        else:
            start = _month_start(today, n - 1)
        end = today + timedelta(days=1)
    else:
        week = today - timedelta(days=today.weekday())  # Monday
        quarter = date(today.year, 3 * ((today.month - 1) // 3) + 1, 1)
        year = date(today.year, 1, 1)
        periods = {
            "today": (today, today + timedelta(days=1)),
            "yesterday": (today - timedelta(days=1), today),
            "this_week": (week, week + timedelta(days=7)),
            "last_week": (week - timedelta(days=7), week),
            "this_month": (_month_start(today), _month_start(today, -1)),
            "last_month": (_month_start(today, 1), _month_start(today)),
            "this_quarter": (quarter, _month_start(quarter, -3)),
            "last_quarter": (_month_start(quarter, 3), quarter),
            "this_year": (year, date(today.year + 1, 1, 1)),
            "ytd": (year, today + timedelta(days=1)),
            "last_year": (date(today.year - 1, 1, 1), year),
        }
        if p not in periods:
            raise SpecError(f"Unknown relative period {period!r}. Use one of: {', '.join(RELATIVE_PERIODS)}")
        start, end = periods[p]
    return datetime.combine(start, time()), datetime.combine(end, time())


def time_bucket(expr: ColumnElement[Any], grain: Grain, dialect: str) -> ColumnElement[Any]:
    """Truncate a timestamp to the start of its day/week (Monday)/month/quarter/year."""
    if dialect == "sqlite":
        # SQLite has no date type: these return 'YYYY-MM-DD' text, parsed by run_query
        weekday = (cast(func.strftime("%w", expr), Integer) + 6) % 7  # Monday = 0
        month = cast(func.strftime("%m", expr), Integer)
        return {
            "day": lambda: func.date(expr),
            "week": lambda: func.date(expr, func.printf("-%d days", weekday)),
            "month": lambda: func.strftime("%Y-%m-01", expr),
            "quarter": lambda: func.printf("%s-%02d-01", func.strftime("%Y", expr), (month - 1) // 3 * 3 + 1),
            "year": lambda: func.strftime("%Y-01-01", expr),
        }[grain]()
    if dialect == "hana":
        day = func.to_date(expr)
        month_start = func.add_days(day, 1 - func.dayofmonth(expr))
        return {
            "day": lambda: day,
            "week": lambda: func.add_days(day, -func.weekday(expr)),  # HANA WEEKDAY: Monday = 0
            "month": lambda: month_start,
            "quarter": lambda: func.add_months(month_start, -func.mod(func.month(expr) - 1, 3)),
            "year": lambda: func.add_days(day, 1 - func.dayofyear(expr)),
        }[grain]()
    return func.date_trunc(grain, expr)  # PostgreSQL and friends


def _coerce(dim: Dimension, field: str, value: Any) -> Any:
    if isinstance(value, bool) or value is None or isinstance(value, list):
        raise SpecError(f"Filter on {field!r} needs a single string or number value, got {value!r}")
    if dim.kind == "temporal":
        try:
            return datetime.fromisoformat(str(value))
        except ValueError:
            raise SpecError(f"Filter on {field!r} needs an ISO date like 2026-01-31, or use op 'relative'") from None
    if dim.kind == "numeric":
        try:
            return float(value)
        except ValueError:
            raise SpecError(f"Filter on {field!r} needs a number, got {value!r}") from None
    return str(value)


def _condition(dim: Dimension, f: Filter, today: date) -> ColumnElement[bool]:
    col, v = dim.column, f.value
    if f.op == "relative":
        if dim.kind != "temporal" or not isinstance(v, str):
            raise SpecError(f"'relative' filters need a temporal field and a period like 'last_week' ({f.field!r})")
        start, end = resolve_relative(v, today)
        return and_(col >= start, col < end)
    if f.op in ("in", "not_in"):
        if not isinstance(v, list) or not v:
            raise SpecError(f"{f.op!r} filter on {f.field!r} needs a non-empty list of values")
        values = [_coerce(dim, f.field, x) for x in v]
        return col.in_(values) if f.op == "in" else col.not_in(values)
    if f.op == "between":
        if not isinstance(v, list) or len(v) != 2:
            raise SpecError(f"'between' filter on {f.field!r} needs [low, high]")
        return col.between(_coerce(dim, f.field, v[0]), _coerce(dim, f.field, v[1]))
    if f.op == "contains":
        if dim.kind not in ("categorical", "text"):
            raise SpecError(f"'contains' only works on text fields, not {f.field!r}")
        return col.icontains(str(_coerce(dim, f.field, v)), autoescape=True)
    return _COMPARISONS[f.op](col, _coerce(dim, f.field, v))


def compile_query(spec: QuerySpec, dialect: str, today: date) -> Select:
    ds = get_dataset(spec.dataset)
    columns: dict[str, ColumnElement[Any]] = {}
    group_by: list[ColumnElement[Any]] = []

    for ref in spec.dimensions:
        if ref.field in columns:
            raise SpecError(f"{ref.field!r} appears twice in the query")
        dim = ds.dimension(ref.field)
        expr = dim.column
        if ref.grain:
            if dim.kind != "temporal":
                raise SpecError(f"Only temporal fields take a grain; {ref.field!r} is {dim.kind}")
            expr = time_bucket(expr, ref.grain, dialect)
        columns[ref.field] = expr
        group_by.append(expr)
    for name in spec.measures:
        if name in columns:
            raise SpecError(f"{name!r} appears twice in the query")
        columns[name] = ds.measure(name).expr
    if not columns:
        raise SpecError("Add at least one dimension or measure")

    stmt = select(*(expr.label(name) for name, expr in columns.items())).select_from(ds.table)
    for f in spec.filters:
        stmt = stmt.where(_condition(ds.dimension(f.field), f, today))
    if spec.measures and group_by:
        stmt = stmt.group_by(*group_by)

    order = []
    for s in spec.sort:
        if s.field not in columns:
            raise SpecError(f"Can only sort by the query's own fields ({', '.join(columns)}), not {s.field!r}")
        order.append(columns[s.field].desc() if s.desc else columns[s.field].asc())
    if not order and group_by:
        temporal = [r.field for r in spec.dimensions if ds.dimensions[r.field].kind == "temporal"]
        if temporal:
            order = [columns[name].asc() for name in temporal]
        elif spec.measures:
            order = [columns[spec.measures[0]].desc()]
        else:
            order = [columns[spec.dimensions[0].field].asc()]
    # One extra row tells us whether the result was cut off
    return stmt.order_by(*order).limit(spec.limit + 1)


def _to_number(s: pd.Series) -> pd.Series:
    # HANA returns SUM/AVG as Decimal
    return pd.to_numeric(s.map(lambda v: float(v) if isinstance(v, Decimal) else v), errors="coerce")


def run_query(session: Session, spec: QuerySpec, today: date | None = None) -> QueryResult:
    ds = get_dataset(spec.dataset)
    today = today or utcnow().date()
    conn = session.connection()
    result = conn.execute(compile_query(spec, conn.dialect.name, today))
    keys = list(result.keys())
    rows = result.all()
    truncated = len(rows) > spec.limit
    df = pd.DataFrame([tuple(r) for r in rows[: spec.limit]], columns=keys)

    for ref in spec.dimensions:
        kind = ds.dimensions[ref.field].kind
        if kind == "temporal":
            df[ref.field] = pd.to_datetime(df[ref.field])
        elif kind == "numeric":
            df[ref.field] = _to_number(df[ref.field])
    for name in spec.measures:
        df[name] = _to_number(df[name])
    return QueryResult(df=df, truncated=truncated)


def distinct_values(session: Session, dataset: str, field: str, search: str = "", limit: int = 100) -> list[Any]:
    """Distinct values of a dimension, to ground filters (e.g. exact category spelling)."""
    col = get_dataset(dataset).dimension(field).column
    stmt = select(col).where(col.is_not(None)).distinct().order_by(col).limit(limit)
    if search:
        stmt = stmt.where(col.icontains(search, autoescape=True))
    values = session.connection().execute(stmt).scalars().all()
    return [v.isoformat() if isinstance(v, date) else float(v) if isinstance(v, Decimal) else v for v in values]
