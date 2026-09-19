"""seed items

Revision ID: 0002
Revises: 0001
Create Date: 2026-09-18

Sample data so the grid and charts have something to show. Delete this revision (and
the rows) once real data exists.
"""

from collections.abc import Sequence
from datetime import UTC, datetime

import sqlalchemy as sa
from alembic import op

revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

SEED = [
    ("Bolt M6", "Hardware", "Zinc plated", 1200),
    ("Nut M6", "Hardware", None, 950),
    ("Washer 6mm", "Hardware", None, 2000),
    ("Copper wire 2.5mm", "Electrical", "Per metre", 430),
    ("Circuit breaker 16A", "Electrical", None, 75),
    ("Safety gloves", "Safety", "Size L", 310),
    ("Hard hat", "Safety", None, 64),
    ("Lubricant 1L", "Consumables", None, 120),
]

# A minimal stand-in for the real table: data migrations must not import the models,
# which keep changing, or this revision would stop reproducing history.
items = sa.table(
    "items",
    sa.column("name", sa.String),
    sa.column("category", sa.String),
    sa.column("description", sa.String),
    sa.column("quantity", sa.Integer),
    sa.column("created_at", sa.TIMESTAMP),
)


def upgrade() -> None:
    now = datetime.now(UTC).replace(tzinfo=None)
    op.bulk_insert(
        items,
        [
            {"name": name, "category": category, "description": description, "quantity": quantity, "created_at": now}
            for name, category, description, quantity in SEED
        ],
    )


def downgrade() -> None:
    op.execute(items.delete().where(items.c.name.in_([name for name, *_ in SEED])))
