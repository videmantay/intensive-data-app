"""Business logic and data access for items, as SQLAlchemy/SQLModel queries.

These plain functions are the single source of truth: the REST endpoints in
router.py call them, and agent tools should call them too. The session is committed
by the request dependency, so these only need `flush()` to get generated ids.
"""

from collections.abc import Sequence

from sqlalchemy import func
from sqlmodel import Session, select

from app.items.models import CategoryTotal, Item, ItemCreate, ItemUpdate


def list_items(session: Session, limit: int = 100, offset: int = 0) -> Sequence[Item]:
    return session.exec(select(Item).order_by(Item.id).limit(limit).offset(offset)).all()


def get_item(session: Session, item_id: int) -> Item | None:
    return session.get(Item, item_id)


def create_item(session: Session, data: ItemCreate) -> Item:
    item = Item.model_validate(data)
    session.add(item)
    session.flush()  # assigns item.id
    return item


def update_item(session: Session, item_id: int, data: ItemUpdate) -> Item | None:
    item = session.get(Item, item_id)
    if item is None:
        return None
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(item, field, value)
    session.add(item)
    session.flush()
    return item


def delete_item(session: Session, item_id: int) -> bool:
    item = session.get(Item, item_id)
    if item is None:
        return False
    session.delete(item)
    return True


def totals_by_category(session: Session) -> list[CategoryTotal]:
    total_quantity = func.sum(Item.quantity).label("total_quantity")
    statement = (
        select(Item.category, total_quantity, func.count().label("item_count"))
        .group_by(Item.category)
        .order_by(total_quantity.desc())
    )
    # SUM() comes back as Decimal on HANA, so coerce to int for the response model
    return [
        CategoryTotal(category=category, total_quantity=int(quantity or 0), item_count=count)
        for category, quantity, count in session.exec(statement).all()
    ]
