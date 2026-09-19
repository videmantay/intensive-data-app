"""Dashboards and widgets, always scoped to their owner.

Every function takes the signed-in user's id. Asking for someone else's dashboard or
widget returns None, exactly like one that doesn't exist, so the router answers 404
and never reveals that it exists. The REST endpoints and the assistant's tools both
call these.
"""

from collections.abc import Sequence

from sqlalchemy import delete, func
from sqlmodel import Session, select

from app.analytics.spec import ChartSpec, QuerySpec, WidgetSpec
from app.dashboards.models import (
    Dashboard,
    DashboardDetail,
    Widget,
    WidgetCreate,
    WidgetPosition,
    WidgetPublic,
    WidgetUpdate,
)
from app.db.types import utcnow

DEFAULT_WIDGET = WidgetSpec(
    query=QuerySpec(dataset="items", dimensions=[{"field": "category"}], measures=["total_quantity"]),
    chart=ChartSpec(type="bar", title="Quantity by category"),
)


def to_public(widget: Widget) -> WidgetPublic:
    return WidgetPublic.model_validate({**widget.model_dump(), "spec": WidgetSpec.model_validate_json(widget.spec)})


def list_dashboards(session: Session, user_id: int) -> Sequence[Dashboard]:
    return session.exec(select(Dashboard).where(Dashboard.owner_id == user_id).order_by(Dashboard.id)).all()


def ensure_dashboard(session: Session, user_id: int) -> None:
    """Give a user with no dashboards a first one, so the page is never empty."""
    if not list_dashboards(session, user_id):
        dashboard = create_dashboard(session, user_id, "My dashboard")
        create_widget(session, user_id, dashboard.id, WidgetCreate(title="", spec=DEFAULT_WIDGET, w=12, h=9))


def get_dashboard(session: Session, user_id: int, dashboard_id: int) -> Dashboard | None:
    dashboard = session.get(Dashboard, dashboard_id)
    return dashboard if dashboard is not None and dashboard.owner_id == user_id else None


def get_dashboard_detail(session: Session, user_id: int, dashboard_id: int) -> DashboardDetail | None:
    dashboard = get_dashboard(session, user_id, dashboard_id)
    if dashboard is None:
        return None
    widgets = session.exec(select(Widget).where(Widget.dashboard_id == dashboard_id).order_by(Widget.y, Widget.x))
    return DashboardDetail.model_validate({**dashboard.model_dump(), "widgets": [to_public(w) for w in widgets]})


def create_dashboard(session: Session, user_id: int, name: str) -> Dashboard:
    dashboard = Dashboard(owner_id=user_id, name=name.strip())
    session.add(dashboard)
    session.flush()
    return dashboard


def rename_dashboard(session: Session, user_id: int, dashboard_id: int, name: str) -> Dashboard | None:
    dashboard = get_dashboard(session, user_id, dashboard_id)
    if dashboard is None:
        return None
    dashboard.name = name.strip()
    dashboard.updated_at = utcnow()
    session.add(dashboard)
    session.flush()
    return dashboard


def delete_dashboard(session: Session, user_id: int, dashboard_id: int) -> bool:
    dashboard = get_dashboard(session, user_id, dashboard_id)
    if dashboard is None:
        return False
    session.exec(delete(Widget).where(Widget.dashboard_id == dashboard_id))
    session.delete(dashboard)
    return True


def get_widget(session: Session, user_id: int, widget_id: int) -> Widget | None:
    widget = session.get(Widget, widget_id)
    if widget is None or get_dashboard(session, user_id, widget.dashboard_id) is None:
        return None
    return widget


def _touch(session: Session, dashboard_id: int) -> None:
    dashboard = session.get(Dashboard, dashboard_id)
    if dashboard is not None:
        dashboard.updated_at = utcnow()
        session.add(dashboard)


def create_widget(session: Session, user_id: int, dashboard_id: int, data: WidgetCreate) -> Widget | None:
    if get_dashboard(session, user_id, dashboard_id) is None:
        return None
    if data.y is None:
        # Below everything already on the dashboard
        bottom = session.exec(select(func.max(Widget.y + Widget.h)).where(Widget.dashboard_id == dashboard_id)).one()
        y = bottom or 0
    else:
        y = data.y
    kpi = data.spec.chart.type == "kpi"
    widget = Widget(
        dashboard_id=dashboard_id,
        title=data.title,
        spec=data.spec.model_dump_json(),
        x=data.x or 0,
        y=y,
        w=data.w or (4 if kpi else 6),
        h=data.h or (4 if kpi else 8),
    )
    session.add(widget)
    _touch(session, dashboard_id)
    session.flush()
    return widget


def update_widget(session: Session, user_id: int, widget_id: int, data: WidgetUpdate) -> Widget | None:
    widget = get_widget(session, user_id, widget_id)
    if widget is None:
        return None
    if data.title is not None:
        widget.title = data.title
    if data.spec is not None:
        widget.spec = data.spec.model_dump_json()
    widget.updated_at = utcnow()
    session.add(widget)
    _touch(session, widget.dashboard_id)
    session.flush()
    return widget


def delete_widget(session: Session, user_id: int, widget_id: int) -> bool:
    widget = get_widget(session, user_id, widget_id)
    if widget is None:
        return False
    _touch(session, widget.dashboard_id)
    session.delete(widget)
    return True


def save_layout(session: Session, user_id: int, dashboard_id: int, positions: list[WidgetPosition]) -> bool:
    """Move and resize widgets. Positions for widgets on other dashboards are ignored."""
    if get_dashboard(session, user_id, dashboard_id) is None:
        return False
    by_id = {p.id: p for p in positions}
    for widget in session.exec(select(Widget).where(Widget.dashboard_id == dashboard_id)):
        if (p := by_id.get(widget.id)) is not None:
            widget.x, widget.y, widget.w, widget.h = p.x, p.y, p.w, p.h
            session.add(widget)
    session.flush()
    return True
