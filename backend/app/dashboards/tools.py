"""Assistant tools for the user's dashboards. They call the same service as the REST endpoints."""

from pydantic import BaseModel
from pydantic_ai import FunctionToolset, ModelRetry, RunContext
from sqlmodel import Session, func, select

from app.analytics.datasets import SpecError
from app.analytics.query import run_query
from app.analytics.spec import WidgetSpec
from app.assistant.deps import AssistantDeps
from app.dashboards import service
from app.dashboards.models import Widget, WidgetCreate

toolset: FunctionToolset[AssistantDeps] = FunctionToolset(max_retries=2)


class DashboardSummary(BaseModel):
    id: int
    name: str
    widget_count: int


class AddedToDashboard(BaseModel):
    added: bool
    message: str
    dashboard_id: int | None = None
    dashboard_name: str | None = None
    widget_id: int | None = None


@toolset.tool
def list_my_dashboards(ctx: RunContext[AssistantDeps]) -> list[DashboardSummary]:
    """The user's dashboards, to pick where to add a chart."""
    with Session(ctx.deps.engine) as session:
        service.ensure_dashboard(session, ctx.deps.user_id)
        session.commit()
        return [
            DashboardSummary(
                id=d.id,
                name=d.name,
                widget_count=session.exec(select(func.count()).where(Widget.dashboard_id == d.id)).one(),
            )
            for d in service.list_dashboards(session, ctx.deps.user_id)
        ]


@toolset.tool
def add_chart_to_dashboard(
    ctx: RunContext[AssistantDeps],
    spec: WidgetSpec,
    title: str = "",
    dashboard_id: int | None = None,
    new_dashboard_name: str | None = None,
) -> AddedToDashboard:
    """Pin a chart to one of the user's dashboards. Only call this when the user asks to keep/add/pin a chart.

    Pass the `spec` from make_chart unchanged (edit it only if the user asked for a change).
    Give `dashboard_id`, or `new_dashboard_name` to create one. With neither, the chart goes
    on the user's only dashboard; if they have several you'll be told to ask which.
    """
    with Session(ctx.deps.engine) as session:
        try:
            run_query(session, spec.query, ctx.deps.today)  # make sure it still runs
        except SpecError as exc:
            raise ModelRetry(str(exc)) from exc

        if new_dashboard_name:
            dashboard = service.create_dashboard(session, ctx.deps.user_id, new_dashboard_name[:100])
        elif dashboard_id is not None:
            dashboard = service.get_dashboard(session, ctx.deps.user_id, dashboard_id)
            if dashboard is None:
                raise ModelRetry(f"There is no dashboard {dashboard_id}. Call list_my_dashboards.")
        else:
            service.ensure_dashboard(session, ctx.deps.user_id)
            dashboards = service.list_dashboards(session, ctx.deps.user_id)
            if len(dashboards) > 1:
                names = ", ".join(f"{d.name} (id {d.id})" for d in dashboards)
                return AddedToDashboard(added=False, message=f"Ask the user which dashboard: {names}")
            dashboard = dashboards[0]

        widget = service.create_widget(session, ctx.deps.user_id, dashboard.id, WidgetCreate(title=title, spec=spec))
        session.commit()
        return AddedToDashboard(
            added=True,
            message=f"Added to {dashboard.name}.",
            dashboard_id=dashboard.id,
            dashboard_name=dashboard.name,
            widget_id=widget.id,
        )
