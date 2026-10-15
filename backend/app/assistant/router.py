"""Assistant endpoints: chat threads, and the chat stream itself.

`assistant_chat` speaks the Vercel AI SDK data-stream protocol, which the frontend's
assistant-ui runtime reads: text, tool calls and tool results stream as they happen,
so charts appear in the chat while the model is still writing.

The browser sends the whole conversation (that's how the AI SDK works), but only its
newest user message is used. Everything before comes from the saved thread, so a
client can't slip fake tool results or instructions into the history.
"""

from fastapi import APIRouter, HTTPException, Request, Response, status
from pydantic import ValidationError
from pydantic_ai.ui.vercel_ai import VercelAIAdapter
from sqlmodel import Session

from app.assistant import agent as assistant_agent
from app.assistant import service
from app.assistant.deps import AssistantDeps
from app.assistant.models import ThreadPublic, ThreadUpdate
from app.assistant.schemas import AssistantStatus, ThreadMessages
from app.auth.deps import CurrentUser
from app.config import AppSettings
from app.db import DbSession
from app.db.types import utcnow

router = APIRouter(prefix="/assistant", tags=["assistant"])


@router.get("/status", response_model=AssistantStatus)
def assistant_status(settings: AppSettings):
    """Lets the UI show whether a key is configured before anyone types."""
    return AssistantStatus(configured=bool(settings.openai_api_key), model=settings.openai_model)


@router.get("/threads", response_model=list[ThreadPublic])
def list_threads(session: DbSession, user: CurrentUser):
    return service.list_threads(session, user.id)


@router.post("/threads", response_model=ThreadPublic, status_code=status.HTTP_201_CREATED)
def create_thread(session: DbSession, user: CurrentUser):
    return service.create_thread(session, user.id)


@router.get("/threads/{thread_id}/messages", response_model=ThreadMessages)
def thread_messages(thread_id: int, session: DbSession, user: CurrentUser):
    thread = service.get_thread(session, user.id, thread_id)
    if thread is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Thread not found")
    return ThreadMessages(messages=service.ui_messages(thread))


@router.patch("/threads/{thread_id}", response_model=ThreadPublic)
def rename_thread(thread_id: int, data: ThreadUpdate, session: DbSession, user: CurrentUser):
    thread = service.rename_thread(session, user.id, thread_id, data.title)
    if thread is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Thread not found")
    return thread


@router.delete("/threads/{thread_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_thread(thread_id: int, session: DbSession, user: CurrentUser):
    if not service.delete_thread(session, user.id, thread_id):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Thread not found")
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/chat")
async def assistant_chat(request: Request, settings: AppSettings, user: CurrentUser):
    """Body: the AI SDK chat request plus `threadId`. Streams the reply."""
    if request.headers.get("content-type", "").split(";")[0].strip() != "application/json":
        raise HTTPException(status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, "Send JSON")
    try:
        model = assistant_agent.build_model(settings)
    except assistant_agent.AssistantNotConfiguredError as exc:
        # Fail before streaming starts, so the UI can show a real error
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, str(exc)) from exc

    try:
        run_input = VercelAIAdapter.build_run_input(await request.body())
    except ValidationError as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "Not a chat request") from exc
    thread_id = (run_input.model_extra or {}).get("threadId")
    user_messages = [m for m in run_input.messages if m.role == "user"]
    if not isinstance(thread_id, int) or not user_messages:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "Need a threadId and a user message")

    engine = request.app.state.engine
    with Session(engine) as session:
        thread = service.get_thread(session, user.id, thread_id)
        if thread is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Thread not found")
        history = service.load_history(thread)
    if run_input.trigger == "regenerate-message":
        history = service.drop_last_turn(history)

    adapter = VercelAIAdapter(
        agent=assistant_agent.build_agent(model),
        run_input=run_input.model_copy(update={"messages": user_messages[-1:]}),
        accept=request.headers.get("accept"),
        sdk_version=7,  # matches the `ai` package the frontend uses
    )

    def save(result) -> None:
        with Session(engine) as session:
            service.save_history(session, user.id, thread_id, result.all_messages())
            session.commit()

    stream = adapter.run_stream(
        message_history=history,
        deps=AssistantDeps(engine=engine, user_id=user.id, today=utcnow().date()),
        on_complete=save,
    )
    return adapter.streaming_response(stream)
