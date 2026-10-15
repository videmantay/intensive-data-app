"""Dashboards and their widgets. Each dashboard belongs to one user.

A widget stores its `WidgetSpec` as JSON text (TEXT/NCLOB, which both SQLite and HANA
handle) plus its position on a 12-column grid. The spec is re-run whenever the widget
is shown, so the chart always reflects current data.
"""

from datetime import datetime

from sqlalchemy import TIMESTAMP, Column, ForeignKey, Identity, Text
from sqlmodel import Field, SQLModel

from app.analytics.spec import WidgetSpec
from app.db.types import ID_TYPE, utcnow


class Dashboard(SQLModel, table=True):
    """The `dashboards` table."""

    __tablename__ = "dashboards"

    id: int | None = Field(default=None, sa_column=Column("id", ID_TYPE, Identity(), primary_key=True))
    owner_id: int = Field(sa_column=Column("owner_id", ID_TYPE, ForeignKey("users.id"), nullable=False, index=True))
    name: str = Field(min_length=1, max_length=100)
    created_at: datetime = Field(default_factory=utcnow, sa_type=TIMESTAMP, nullable=False)
    updated_at: datetime = Field(default_factory=utcnow, sa_type=TIMESTAMP, nullable=False)


class Widget(SQLModel, table=True):
    """The `widgets` table. `spec` holds a WidgetSpec as JSON."""

    __tablename__ = "widgets"

    id: int | None = Field(default=None, sa_column=Column("id", ID_TYPE, Identity(), primary_key=True))
    dashboard_id: int = Field(
        sa_column=Column(
            "dashboard_id", ID_TYPE, ForeignKey("dashboards.id", ondelete="CASCADE"), nullable=False, index=True
        )
    )
    title: str = Field(default="", max_length=200)
    spec: str = Field(sa_type=Text, nullable=False)
    x: int = Field(default=0, ge=0)
    y: int = Field(default=0, ge=0)
    w: int = Field(default=6, ge=1, le=12)
    h: int = Field(default=8, ge=2, le=40)
    created_at: datetime = Field(default_factory=utcnow, sa_type=TIMESTAMP, nullable=False)
    updated_at: datetime = Field(default_factory=utcnow, sa_type=TIMESTAMP, nullable=False)


class DashboardCreate(SQLModel):
    """A new dashboard."""

    name: str = Field(min_length=1, max_length=100)


class DashboardUpdate(SQLModel):
    """Rename a dashboard."""

    name: str = Field(min_length=1, max_length=100)


class DashboardPublic(SQLModel):
    """A dashboard, without its widgets."""

    id: int
    name: str
    created_at: datetime
    updated_at: datetime


class WidgetPublic(SQLModel):
    """A widget and where it sits on the grid."""

    id: int
    dashboard_id: int
    title: str
    spec: WidgetSpec
    x: int
    y: int
    w: int
    h: int


class DashboardDetail(DashboardPublic):
    """A dashboard with its widgets."""

    widgets: list[WidgetPublic]


class WidgetCreate(SQLModel):
    """A new widget; without a position it goes below the existing ones."""

    title: str = Field(default="", max_length=200)
    spec: WidgetSpec
    x: int | None = Field(default=None, ge=0)
    y: int | None = Field(default=None, ge=0)
    w: int | None = Field(default=None, ge=1, le=12)
    h: int | None = Field(default=None, ge=2, le=40)


class WidgetUpdate(SQLModel):
    """Only the fields you send are changed."""

    title: str | None = Field(default=None, max_length=200)
    spec: WidgetSpec | None = None


class WidgetPosition(SQLModel):
    """A widget's place on the 12-column grid."""

    id: int
    x: int = Field(ge=0)
    y: int = Field(ge=0)
    w: int = Field(ge=1, le=12)
    h: int = Field(ge=2, le=40)
