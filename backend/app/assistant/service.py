"""Saved chat threads, always scoped to their owner (like dashboards).

A thread stores the whole pydantic-ai conversation, tool calls included, so a reloaded
thread shows the same charts and the model sees exactly what it saw before.
"""

from collections.abc import Sequence
from typing import Any

from pydantic_ai.messages import ModelMessage, ModelMessagesTypeAdapter, ModelRequest, UserPromptPart
from pydantic_ai.ui.vercel_ai import VercelAIAdapter
from sqlmodel import Session, select

from app.assistant.models import NEW_THREAD_TITLE, ChatThread
from app.db.types import utcnow


def list_threads(session: Session, user_id: int) -> Sequence[ChatThread]:
    statement = select(ChatThread).where(ChatThread.owner_id == user_id).order_by(ChatThread.updated_at.desc())
    return session.exec(statement).all()


def create_thread(session: Session, user_id: int) -> ChatThread:
    thread = ChatThread(owner_id=user_id)
    session.add(thread)
    session.flush()
    return thread


def get_thread(session: Session, user_id: int, thread_id: int) -> ChatThread | None:
    thread = session.get(ChatThread, thread_id)
    return thread if thread is not None and thread.owner_id == user_id else None


def rename_thread(session: Session, user_id: int, thread_id: int, title: str) -> ChatThread | None:
    thread = get_thread(session, user_id, thread_id)
    if thread is None:
        return None
    thread.title = title.strip()
    session.add(thread)
    session.flush()
    return thread


def delete_thread(session: Session, user_id: int, thread_id: int) -> bool:
    thread = get_thread(session, user_id, thread_id)
    if thread is None:
        return False
    session.delete(thread)
    return True


def load_history(thread: ChatThread) -> list[ModelMessage]:
    return ModelMessagesTypeAdapter.validate_json(thread.messages)


def _first_prompt(messages: Sequence[ModelMessage]) -> str:
    for message in messages:
        if isinstance(message, ModelRequest):
            for part in message.parts:
                if isinstance(part, UserPromptPart) and isinstance(part.content, str):
                    return part.content
    return ""


def save_history(session: Session, user_id: int, thread_id: int, messages: Sequence[ModelMessage]) -> None:
    thread = get_thread(session, user_id, thread_id)
    if thread is None:
        return
    thread.messages = ModelMessagesTypeAdapter.dump_json(list(messages)).decode()
    if thread.title == NEW_THREAD_TITLE and (prompt := _first_prompt(messages)):
        # Name the thread after its first question
        thread.title = prompt if len(prompt) <= 60 else prompt[:57].rstrip() + "…"
    thread.updated_at = utcnow()
    session.add(thread)
    session.flush()


def drop_last_turn(history: list[ModelMessage]) -> list[ModelMessage]:
    """History before the latest user prompt, for "regenerate": that turn is run again."""
    for i in range(len(history) - 1, -1, -1):
        message = history[i]
        if isinstance(message, ModelRequest) and any(isinstance(p, UserPromptPart) for p in message.parts):
            return history[:i]
    return history


def ui_messages(thread: ChatThread) -> list[dict[str, Any]]:
    """The thread as Vercel AI SDK UI messages, for the chat to show on load."""
    merged: list[dict[str, Any]] = []
    for message in VercelAIAdapter.dump_messages(load_history(thread)):
        data = message.model_dump(mode="json", by_alias=True, exclude_none=True)
        # One reply can span several model responses (tool call, then text); the live
        # stream shows them as one message, so do the same here
        if merged and data["role"] == "assistant" and merged[-1]["role"] == "assistant":
            merged[-1]["parts"].extend(data["parts"])
        else:
            merged.append(data)
    return merged
