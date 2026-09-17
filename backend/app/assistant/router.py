"""Assistant endpoints.

`chat_stream` streams plain UTF-8 text chunks as they arrive from the model. The
frontend's chat adapter (src/lib/assistantAdapter.ts) appends them as they come in.
"""

import logging
from collections.abc import Iterator

from fastapi import APIRouter, HTTPException, status
from fastapi.responses import StreamingResponse

from app.assistant import service
from app.assistant.schemas import AssistantStatus, ChatRequest
from app.assistant.service import AssistantNotConfiguredError
from app.config import AppSettings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/assistant", tags=["assistant"])


@router.get("/status", response_model=AssistantStatus)
def assistant_status(settings: AppSettings):
    """Lets the UI show whether a key is configured before anyone types."""
    return AssistantStatus(configured=bool(settings.openai_api_key), model=settings.openai_model)


@router.post("/chat")
def assistant_chat(request: ChatRequest, settings: AppSettings):
    def generate() -> Iterator[str]:
        try:
            yield from service.stream_reply(settings, request.messages)
        except Exception:
            # The response has already started, so surface the failure in the text itself
            logger.exception("Assistant stream failed")
            yield "\n\n[The assistant hit an error. Check the backend logs.]"

    try:
        # Fail before streaming starts if the key is missing, so the UI can show a real error
        service.check_configured(settings)
    except AssistantNotConfiguredError as exc:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, str(exc)) from exc

    return StreamingResponse(generate(), media_type="text/plain; charset=utf-8")
