"""Chat with an OpenAI model.

Kept separate from the HTTP layer so agent tooling can reuse it later. To give the
assistant access to app data, pass OpenAI `tools` here and run the tool calls against
each feature's service.py functions.
"""

from collections.abc import Iterator

from openai import OpenAI

from app.assistant.prompts import SYSTEM_PROMPT
from app.assistant.schemas import ChatMessage
from app.config import Settings


class AssistantNotConfiguredError(RuntimeError):
    """Raised when no OpenAI API key is configured."""


def check_configured(settings: Settings) -> None:
    """Raise if the assistant can't run, so callers can fail before streaming starts."""
    if not settings.openai_api_key:
        raise AssistantNotConfiguredError("No OpenAI API key. Set OPENAI_API_KEY in backend/.env (see .env.example).")


def _client(settings: Settings) -> OpenAI:
    check_configured(settings)
    return OpenAI(
        api_key=settings.openai_api_key,
        # Optional: point at Azure OpenAI or another OpenAI-compatible gateway
        base_url=settings.openai_base_url or None,
        timeout=settings.openai_timeout_seconds,
    )


def stream_reply(settings: Settings, messages: list[ChatMessage]) -> Iterator[str]:
    """Yield reply text chunks as the model produces them."""
    client = _client(settings)
    stream = client.chat.completions.create(
        model=settings.openai_model,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            *({"role": m.role, "content": m.content} for m in messages),
        ],
        stream=True,
    )
    for chunk in stream:
        if not chunk.choices:
            continue
        text = chunk.choices[0].delta.content
        if text:
            yield text
