"""REST endpoints for items. Keep these thin: validate input, call service/charts, return.

Function names become the generated frontend function names (e.g. `list_items` ->
`listItemsOptions()`), so keep them unique across the whole app.
"""

from fastapi import APIRouter, HTTPException, Query, Response, status

from app.charts import PlotlyFigure, figure_response
from app.db import DbSession
from app.items import charts, service
from app.items.models import CategoryTotal, ItemCreate, ItemPublic, ItemUpdate

router = APIRouter(prefix="/items", tags=["items"])


@router.get("", response_model=list[ItemPublic])
def list_items(
    session: DbSession,
    limit: int = Query(default=100, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
):
    return service.list_items(session, limit, offset)


@router.get("/totals", response_model=list[CategoryTotal])
def item_totals_by_category(session: DbSession):
    return service.totals_by_category(session)


@router.get("/charts/quantity-by-category", response_model=PlotlyFigure)
def item_quantity_chart(session: DbSession):
    return figure_response(charts.quantity_by_category(session))


@router.get("/{item_id}", response_model=ItemPublic)
def get_item(item_id: int, session: DbSession):
    item = service.get_item(session, item_id)
    if item is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Item not found")
    return item


@router.post("", response_model=ItemPublic, status_code=status.HTTP_201_CREATED)
def create_item(data: ItemCreate, session: DbSession):
    return service.create_item(session, data)


@router.patch("/{item_id}", response_model=ItemPublic)
def update_item(item_id: int, data: ItemUpdate, session: DbSession):
    item = service.update_item(session, item_id, data)
    if item is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Item not found")
    return item


@router.delete("/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_item(item_id: int, session: DbSession):
    if not service.delete_item(session, item_id):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Item not found")
    return Response(status_code=status.HTTP_204_NO_CONTENT)
