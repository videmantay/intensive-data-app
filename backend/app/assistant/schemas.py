from typing import Any

from pydantic import BaseModel


class AssistantStatus(BaseModel):
    configured: bool
    model: str


class ThreadMessages(BaseModel):
    """A thread's messages in the Vercel AI SDK `UIMessage` shape."""

    messages: list[dict[str, Any]]
