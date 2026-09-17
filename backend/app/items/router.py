"""REST endpoints for items. Keep these thin: validate input, call service/charts, return.

Function names become the generated frontend function names (e.g. `list_items` ->
`listItemsOptions()`), so keep them unique across the whole app.
"""

from fastapi import APIRouter, HTTPException, Query, Response, status

from app.charts import PlotlyFigure, figure_response
from app.db import DbConn
from app.items import charts, service
from app.items.schemas import CategoryTotal, Item, ItemCreate, ItemUpdate

router = APIRouter(prefix="/items", tags=["items"])


@router.get("", response_model=list[Item])
def list_items(
    conn: DbConn,
    limit: int = Query(default=100, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
):
    return service.list_items(conn, limit, offset)


@router.get("/totals", response_model=list[CategoryTotal])
def item_totals_by_category(conn: DbConn):
    return service.totals_by_category(conn)


@router.get("/charts/quantity-by-category", response_model=PlotlyFigure)
def item_quantity_chart(conn: DbConn):
    return figure_response(charts.quantity_by_category(conn))


@router.get("/{item_id}", response_model=Item)
def get_item(item_id: int, conn: DbConn):
    item = service.get_item(conn, item_id)
    if item is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Item not found")
    return item


@router.post("", response_model=Item, status_code=status.HTTP_201_CREATED)
def create_item(data: ItemCreate, conn: DbConn):
    return service.create_item(conn, data)


@router.patch("/{item_id}", response_model=Item)
def update_item(item_id: int, data: ItemUpdate, conn: DbConn):
    item = service.update_item(conn, item_id, data)
    if item is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Item not found")
    return item


@router.delete("/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_item(item_id: int, conn: DbConn):
    if not service.delete_item(conn, item_id):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Item not found")
    return Response(status_code=status.HTTP_204_NO_CONTENT)
