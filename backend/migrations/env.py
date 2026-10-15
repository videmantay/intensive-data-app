"""Alembic environment.

Autogenerate compares the SQLModel metadata against the live database, so every
table needs its models module imported below.
"""

from alembic import context
from sqlalchemy import Engine
from sqlmodel import SQLModel

from app.assistant import models as assistant_models  # noqa: F401  (CHAT_THREADS)
from app.auth import models as auth_models  # noqa: F401  (registers the USERS table)
from app.config import get_settings
from app.dashboards import models as dashboards_models  # noqa: F401  (DASHBOARDS, WIDGETS)
from app.db import create_db_engine
from app.items import models as items_models  # noqa: F401  (registers the ITEMS table)

target_metadata = SQLModel.metadata


def _engine() -> tuple[Engine, bool]:
    """The engine app/main.py passed in, or a fresh one from settings. Returns (engine, owned)."""
    engine = context.config.attributes.get("engine")
    if engine is not None:
        return engine, False
    return create_db_engine(get_settings()), True


def run_migrations_offline() -> None:
    engine, owned = _engine()
    try:
        context.configure(url=engine.url, target_metadata=target_metadata, literal_binds=True)
        with context.begin_transaction():
            context.run_migrations()
    finally:
        if owned:
            engine.dispose()


def run_migrations_online() -> None:
    engine, owned = _engine()
    try:
        with engine.connect() as connection:
            context.configure(
                connection=connection,
                target_metadata=target_metadata,
                # SQLite cannot ALTER most things in place; batch mode rewrites the table
                render_as_batch=connection.dialect.name == "sqlite",
            )
            with context.begin_transaction():
                context.run_migrations()
    finally:
        if owned:
            engine.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
