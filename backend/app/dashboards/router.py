"""REST endpoints for dashboards and widgets. All of them act on the signed-in user's own dashboards."""

from fastapi import APIRouter, HTTPException, Response, status

from app.analytics.datasets import SpecError
from app.analytics.service import run_widget
from app.analytics.spec import WidgetResult, WidgetSpec
from app.auth.deps import CurrentUser
from app.dashboards import service
from app.dashboards.models import (
    DashboardCreate,
    DashboardDetail,
    DashboardPublic,
    DashboardUpdate,
    WidgetCreate,
    WidgetPosition,
    WidgetPublic,
    WidgetUpdate,
)
from app.db import DbSession

router = APIRouter(tags=["dashboards"])


def _not_found(what: str) -> HTTPException:
    return HTTPException(status.HTTP_404_NOT_FOUND, f"{what} not found")


@router.get("/dashboards", response_model=list[DashboardPublic])
def list_dashboards(session: DbSession, user: CurrentUser):
    service.ensure_dashboard(session, user.id)
    return service.list_dashboards(session, user.id)


@router.post("/dashboards", response_model=DashboardPublic, status_code=status.HTTP_201_CREATED)
def create_dashboard(data: DashboardCreate, session: DbSession, user: CurrentUser):
    return service.create_dashboard(session, user.id, data.name)


@router.get("/dashboards/{dashboard_id}", response_model=DashboardDetail)
def get_dashboard(dashboard_id: int, session: DbSession, user: CurrentUser):
    detail = service.get_dashboard_detail(session, user.id, dashboard_id)
    if detail is None:
        raise _not_found("Dashboard")
    return detail


@router.patch("/dashboards/{dashboard_id}", response_model=DashboardPublic)
def rename_dashboard(dashboard_id: int, data: DashboardUpdate, session: DbSession, user: CurrentUser):
    dashboard = service.rename_dashboard(session, user.id, dashboard_id, data.name)
    if dashboard is None:
        raise _not_found("Dashboard")
    return dashboard


@router.delete("/dashboards/{dashboard_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_dashboard(dashboard_id: int, session: DbSession, user: CurrentUser):
    if not service.delete_dashboard(session, user.id, dashboard_id):
        raise _not_found("Dashboard")
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.put("/dashboards/{dashboard_id}/layout", status_code=status.HTTP_204_NO_CONTENT)
def save_dashboard_layout(dashboard_id: int, positions: list[WidgetPosition], session: DbSession, user: CurrentUser):
    if not service.save_layout(session, user.id, dashboard_id, positions):
        raise _not_found("Dashboard")
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/dashboards/{dashboard_id}/widgets", response_model=WidgetPublic, status_code=status.HTTP_201_CREATED)
def create_widget(dashboard_id: int, data: WidgetCreate, session: DbSession, user: CurrentUser):
    widget = service.create_widget(session, user.id, dashboard_id, data)
    if widget is None:
        raise _not_found("Dashboard")
    return service.to_public(widget)


@router.patch("/widgets/{widget_id}", response_model=WidgetPublic)
def update_widget(widget_id: int, data: WidgetUpdate, session: DbSession, user: CurrentUser):
    widget = service.update_widget(session, user.id, widget_id, data)
    if widget is None:
        raise _not_found("Widget")
    return service.to_public(widget)


@router.delete("/widgets/{widget_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_widget(widget_id: int, session: DbSession, user: CurrentUser):
    if not service.delete_widget(session, user.id, widget_id):
        raise _not_found("Widget")
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/widgets/{widget_id}/data", response_model=WidgetResult)
def widget_data(widget_id: int, session: DbSession, user: CurrentUser):
    widget = service.get_widget(session, user.id, widget_id)
    if widget is None:
        raise _not_found("Widget")
    try:
        result = run_widget(session, WidgetSpec.model_validate_json(widget.spec))
    except SpecError as exc:
        # e.g. a field was removed from the dataset after the widget was saved
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, str(exc)) from exc
    return result.model_copy(update={"title": widget.title or result.title})
