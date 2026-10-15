"""What every assistant tool receives as `ctx.deps`."""

from dataclasses import dataclass
from datetime import date

from sqlalchemy import Engine


@dataclass
class AssistantDeps:
    # Tools open their own short sessions: the chat response streams after the
    # request's own session has closed.
    engine: Engine
    user_id: int
    today: date
