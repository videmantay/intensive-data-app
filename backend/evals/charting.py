"""Check which charts the real model picks for typical questions.

Runs each question through the assistant (with your OPENAI_API_KEY) against a fresh,
seeded SQLite database and compares the first chart it draws with what we expect.
Run it after changing prompts.py, skills/charting.md or the model:

    uv run python -m evals.charting

It costs a few cents per run. It's not part of `pytest` because model answers vary;
treat a drop in the score as a signal to read the transcripts, not as a hard failure.
"""

import asyncio
import tempfile
from dataclasses import dataclass
from pathlib import Path

from pydantic_ai.messages import ToolCallPart, ToolReturnPart
from sqlmodel import Session

from app.assistant.agent import build_agent, build_model
from app.assistant.deps import AssistantDeps
from app.auth.service import create_user
from app.config import Settings, get_settings
from app.db import create_db_engine
from app.db.migrate import run_migrations
from app.db.types import utcnow


@dataclass
class Case:
    question: str
    chart: str | None  # expected chart_type drawn, or None when no chart should be drawn
    note: str = ""  # something the reply should mention, e.g. the better chart


CASES = [
    Case("Show total quantity by category", "bar"),
    Case("What share of all stock does each category have?", "donut"),
    Case("How is quantity per item distributed?", "histogram"),
    Case("Compare the spread of quantities across categories", "box"),
    Case("How many items do we have in total?", None),
    Case("Which category has the most stock?", None),
    Case("Show quantity by category as a radar chart", "radar", note="bar"),
    Case("Line chart of quantity by category", "bar", note="time"),
    Case("Items added per week", "line"),
    Case("Top 5 items by quantity", "bar"),
    Case("Quantity by category and item", "bar"),
]


def first_chart(messages) -> str | None:
    for message in messages:
        for part in getattr(message, "parts", []):
            if isinstance(part, ToolReturnPart) and part.tool_name == "make_chart":
                return getattr(part.content, "chart_type", None)  # a ChartResult
    return None


def tools_used(messages) -> list[str]:
    return [p.tool_name for m in messages for p in getattr(m, "parts", []) if isinstance(p, ToolCallPart)]


async def main() -> None:
    settings = get_settings()
    agent = build_agent(build_model(settings))
    with tempfile.TemporaryDirectory() as tmp:
        engine = create_db_engine(Settings(sqlite_path=Path(tmp) / "eval.db"))
        run_migrations(engine)
        with Session(engine) as session:
            user = create_user(session, "eval", "not-used")
            session.commit()
        deps = AssistantDeps(engine=engine, user_id=user.id, today=utcnow().date())

        passed = 0
        for case in CASES:
            result = await agent.run(case.question, deps=deps)
            messages = result.all_messages()
            drawn = first_chart(messages)
            ok = drawn == case.chart and (not case.note or case.note in result.output.lower())
            passed += ok
            print(f"{'PASS' if ok else 'FAIL'}  {case.question}")
            print(f"      expected {case.chart}, drew {drawn}; tools: {', '.join(tools_used(messages)) or 'none'}")
            if not ok:
                print(f"      reply: {result.output[:300]}")
        engine.dispose()
    print(f"\n{passed}/{len(CASES)} passed with {settings.openai_model}")


if __name__ == "__main__":
    asyncio.run(main())
