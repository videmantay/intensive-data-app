"""SQLModel models for users. Passwords are stored only as argon2 hashes."""

from datetime import datetime

from sqlalchemy import TIMESTAMP, Column, Identity
from sqlmodel import Field, SQLModel

from app.db.types import ID_TYPE, utcnow


class User(SQLModel, table=True):
    """The `users` table. Endpoints return `UserPublic`, not this."""

    __tablename__ = "users"

    id: int | None = Field(
        default=None,
        sa_column=Column("id", ID_TYPE, Identity(), primary_key=True),
    )
    # Stored lowercase so logins are case-insensitive
    username: str = Field(min_length=1, max_length=100, unique=True, index=True)
    display_name: str = Field(default="", max_length=255)
    password_hash: str = Field(max_length=255)
    created_at: datetime = Field(default_factory=utcnow, sa_type=TIMESTAMP, nullable=False)


class UserPublic(SQLModel):
    """The signed-in user."""

    id: int
    username: str
    display_name: str


class LoginRequest(SQLModel):
    """Username and password."""

    username: str = Field(min_length=1, max_length=100)
    password: str = Field(min_length=1, max_length=1000)
