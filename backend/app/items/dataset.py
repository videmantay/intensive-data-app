"""The `items` dataset: what the widget builder and the assistant can chart about items."""

from sqlalchemy import func

from app.analytics.datasets import Dataset, Dimension, Measure
from app.items.models import Item

ITEMS = Dataset(
    name="items",
    label="Inventory items",
    description="One row per inventory item, with its category and quantity on hand.",
    table=Item,
    dimensions={
        "category": Dimension(Item.category, "Category", "categorical"),
        "name": Dimension(Item.name, "Item", "categorical"),
        "created_at": Dimension(Item.created_at, "Created", "temporal", "When the item was added"),
        # Raw quantity per item, for distributions (histogram, box plot)
        "quantity": Dimension(Item.quantity, "Quantity", "numeric", "Quantity on hand for a single item"),
    },
    measures={
        "total_quantity": Measure(func.sum(Item.quantity), "Total quantity", "Sum of quantity on hand"),
        "item_count": Measure(func.count(Item.id), "Items", "Number of items"),
        "avg_quantity": Measure(func.avg(Item.quantity), "Average quantity", "Average quantity per item"),
    },
)
