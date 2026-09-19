"""Runs Alembic migrations against a given engine.

Called at startup from `app/main.py`, so a fresh checkout or a new test database is
migrated automatically. Run manually with:

    uv run python -m app.db.migrate

To add a migration, change the models then autogenerate a revision:

    uv run alembic revision --autogenerate -m "add orders"
"""

import logging

from alembic import command
from alembic.config import Config
from sqlalchemy import Engine

from app.config import BACKEND_DIR

logger = logging.getLogger(__name__)

ALEMBIC_INI = BACKEND_DIR / "alembic.ini"


def alembic_config(engine: Engine | None = None) -> Config:
    config = Config(ALEMBIC_INI)
    config.set_main_option("script_location", str(BACKEND_DIR / "migrations"))
    if engine is not None:
        # env.py uses this engine instead of building one from settings
        config.attributes["engine"] = engine
    return config


def run_migrations(engine: Engine) -> None:
    logger.info("Upgrading database to head")
    command.upgrade(alembic_config(engine), "head")


if __name__ == "__main__":
    from app.config import get_settings
    from app.db import create_db_engine

    logging.basicConfig(level=logging.INFO)
    settings = get_settings()
    engine = create_db_engine(settings)
    try:
        run_migrations(engine)
    finally:
        engine.dispose()
    print(f"Database at {engine.url.render_as_string(hide_password=True)} is up to date")
