"""The pydantic-ai agent: model, instructions and tools.

Tools live with their feature (`app/<feature>/tools.py`) and call the same service
functions as the REST endpoints. To give the assistant a new ability, add a tool there
and list its toolset in `TOOLSETS`.
"""

from openai import AsyncOpenAI
from pydantic_ai import Agent, RunContext
from pydantic_ai.models import Model
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.openai import OpenAIProvider

from app.analytics.registry import catalog
from app.analytics.tools import toolset as analytics_tools
from app.assistant.deps import AssistantDeps
from app.assistant.prompts import CHARTING_GUIDE, SYSTEM_PROMPT
from app.config import Settings
from app.dashboards.tools import toolset as dashboard_tools

TOOLSETS = [analytics_tools, dashboard_tools]


class AssistantNotConfiguredError(RuntimeError):
    """Raised when no OpenAI API key is configured."""


def check_configured(settings: Settings) -> None:
    """Raise if the assistant can't run, so callers can fail before streaming starts."""
    if not settings.openai_api_key:
        raise AssistantNotConfiguredError("No OpenAI API key. Set OPENAI_API_KEY in backend/.env (see .env.example).")


def build_model(settings: Settings) -> Model:
    """The OpenAI model from settings. Tests replace this with a scripted model."""
    check_configured(settings)
    client = AsyncOpenAI(
        api_key=settings.openai_api_key,
        # Optional: point at Azure OpenAI or another OpenAI-compatible gateway
        base_url=settings.openai_base_url or None,
        timeout=settings.openai_timeout_seconds,
    )
    return OpenAIChatModel(settings.openai_model, provider=OpenAIProvider(openai_client=client))


def _context(ctx: RunContext[AssistantDeps]) -> str:
    return f"Today is {ctx.deps.today:%A %Y-%m-%d}.\n\n# Datasets\n\n{catalog()}"


def build_agent(model: Model) -> Agent[AssistantDeps, str]:
    return Agent(
        model,
        deps_type=AssistantDeps,
        instructions=[SYSTEM_PROMPT, CHARTING_GUIDE, _context],
        toolsets=TOOLSETS,
    )
