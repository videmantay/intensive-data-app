"""Endpoints for the widget builder: what can be queried, and a live preview."""

from typing import Any

from fastapi import APIRouter, HTTPException, Query, status

from app.analytics import service
from app.analytics.datasets import SpecError
from app.analytics.query import distinct_values
from app.analytics.registry import DATASETS
from app.analytics.spec import DatasetInfo, WidgetResult, WidgetSpec
from app.db import DbSession

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/datasets", response_model=list[DatasetInfo])
def list_datasets():
    return [ds.info() for ds in DATASETS.values()]


@router.get("/datasets/{dataset}/values/{field}", response_model=list[Any])
def dimension_values(
    dataset: str,
    field: str,
    session: DbSession,
    search: str = Query(default="", max_length=100),
    limit: int = Query(default=100, ge=1, le=500),
):
    try:
        return distinct_values(session, dataset, field, search, limit)
    except SpecError as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, str(exc)) from exc


@router.post("/preview", response_model=WidgetResult)
def preview_widget(spec: WidgetSpec, session: DbSession):
    try:
        return service.run_widget(session, spec)
    except SpecError as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, str(exc)) from exc
