"""Minimal migration runner.

Applies `app/sql/migrations/*.sql` (SAP HANA dialect) in filename order and
records each one in SCHEMA_MIGRATIONS. Run manually with:

    uv run python -m app.db.migrate
"""

import logging
from pathlib import Path

from app.db.base import Connection, Database

MIGRATIONS_DIR = Path(__file__).resolve().parent.parent / "sql" / "migrations"

logger = logging.getLogger(__name__)

_CREATE_MIGRATIONS_TABLE = """
CREATE COLUMN TABLE SCHEMA_MIGRATIONS (
    VERSION     NVARCHAR(255) PRIMARY KEY,
    APPLIED_AT  TIMESTAMP NOT NULL DEFAULT CURRENT_UTCTIMESTAMP
)
"""


def split_statements(script: str) -> list[str]:
    """Split a script on `;` terminators, ignoring `--` comment lines."""
    lines = [line for line in script.splitlines() if not line.strip().startswith("--")]
    return [stmt.strip() for stmt in "\n".join(lines).split(";") if stmt.strip()]


def _applied_versions(conn: Connection) -> set[str]:
    if not conn.table_exists("SCHEMA_MIGRATIONS"):
        conn.execute(_CREATE_MIGRATIONS_TABLE)
        return set()
    return {row["version"] for row in conn.fetch_all("SELECT VERSION FROM SCHEMA_MIGRATIONS")}


def run_migrations(database: Database) -> list[str]:
    conn = database.connect()
    applied: list[str] = []
    try:
        done = _applied_versions(conn)
        for path in sorted(MIGRATIONS_DIR.glob("*.sql")):
            if path.stem in done:
                continue
            logger.info("Applying migration %s", path.name)
            for statement in split_statements(path.read_text(encoding="utf-8")):
                conn.execute(statement)
            conn.execute("INSERT INTO SCHEMA_MIGRATIONS (VERSION) VALUES (?)", (path.stem,))
            conn.commit()
            applied.append(path.stem)
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
    return applied


if __name__ == "__main__":
    from app.config import get_settings
    from app.db import create_database

    logging.basicConfig(level=logging.INFO)
    result = run_migrations(create_database(get_settings()))
    print(f"Applied: {', '.join(result) or 'nothing (up to date)'}")
