from datetime import datetime

from pydantic import BaseModel, Field


class ItemCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    category: str = Field(default="General", min_length=1, max_length=100)
    description: str | None = Field(default=None, max_length=2000)
    quantity: int = Field(default=0, ge=0)


class ItemUpdate(BaseModel):
    """Every field is optional; only the fields you send are changed."""

    name: str | None = Field(default=None, min_length=1, max_length=255)
    category: str | None = Field(default=None, min_length=1, max_length=100)
    description: str | None = Field(default=None, max_length=2000)
    quantity: int | None = Field(default=None, ge=0)


class Item(ItemCreate):
    id: int
    created_at: datetime


class CategoryTotal(BaseModel):
    category: str
    total_quantity: int
    item_count: int
