"""Business logic and data access for items. All SQL is SAP HANA dialect.

These plain functions are the single source of truth: the REST endpoints in
router.py call them, and agent tools should call them too.
"""

from app.db.base import Connection, Row
from app.items.schemas import ItemCreate, ItemUpdate

_COLUMNS = "ID, NAME, CATEGORY, DESCRIPTION, QUANTITY, CREATED_AT"


def list_items(conn: Connection, limit: int = 100, offset: int = 0) -> list[Row]:
    return conn.fetch_all(
        f"SELECT {_COLUMNS} FROM ITEMS ORDER BY ID LIMIT ? OFFSET ?",
        (limit, offset),
    )


def get_item(conn: Connection, item_id: int) -> Row | None:
    return conn.fetch_one(f"SELECT {_COLUMNS} FROM ITEMS WHERE ID = ?", (item_id,))


def create_item(conn: Connection, data: ItemCreate) -> Row:
    new_id = conn.insert(
        "INSERT INTO ITEMS (NAME, CATEGORY, DESCRIPTION, QUANTITY) VALUES (?, ?, ?, ?)",
        (data.name, data.category, data.description, data.quantity),
    )
    row = get_item(conn, new_id)
    assert row is not None
    return row


def update_item(conn: Connection, item_id: int, data: ItemUpdate) -> Row | None:
    fields = data.model_dump(exclude_unset=True)
    if fields:
        # Column names come from the Pydantic model, never from user input
        assignments = ", ".join(f"{name.upper()} = ?" for name in fields)
        conn.execute(f"UPDATE ITEMS SET {assignments} WHERE ID = ?", (*fields.values(), item_id))
    return get_item(conn, item_id)


def delete_item(conn: Connection, item_id: int) -> bool:
    return conn.execute("DELETE FROM ITEMS WHERE ID = ?", (item_id,)) > 0


def totals_by_category(conn: Connection) -> list[Row]:
    return conn.fetch_all(
        """
        SELECT CATEGORY,
               SUM(QUANTITY) AS TOTAL_QUANTITY,
               COUNT(*)      AS ITEM_COUNT
          FROM ITEMS
         GROUP BY CATEGORY
         ORDER BY TOTAL_QUANTITY DESC
        """
    )
