"""Saved chat threads. Each belongs to one user.

`messages` holds the conversation as pydantic-ai's own JSON (ModelMessagesTypeAdapter),
including tool calls and their results. The server's copy is the source of truth: the
browser only ever sends the newest user message.
"""

from datetime import datetime

from sqlalchemy import TIMESTAMP, Column, ForeignKey, Identity, Text
from sqlmodel import Field, SQLModel

from app.db.types import ID_TYPE, utcnow

NEW_THREAD_TITLE = "New chat"


class ChatThread(SQLModel, table=True):
    """The `chat_threads` table."""

    __tablename__ = "chat_threads"

    id: int | None = Field(default=None, sa_column=Column("id", ID_TYPE, Identity(), primary_key=True))
    owner_id: int = Field(sa_column=Column("owner_id", ID_TYPE, ForeignKey("users.id"), nullable=False, index=True))
    title: str = Field(default=NEW_THREAD_TITLE, max_length=200)
    messages: str = Field(default="[]", sa_type=Text, nullable=False)
    created_at: datetime = Field(default_factory=utcnow, sa_type=TIMESTAMP, nullable=False)
    updated_at: datetime = Field(default_factory=utcnow, sa_type=TIMESTAMP, nullable=False)


class ThreadPublic(SQLModel):
    """A chat thread, without its messages."""

    id: int
    title: str
    created_at: datetime
    updated_at: datetime


class ThreadUpdate(SQLModel):
    """Rename a thread."""

    title: str = Field(min_length=1, max_length=200)
