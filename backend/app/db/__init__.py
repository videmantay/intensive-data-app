from collections.abc import Iterator
from typing import Annotated

from fastapi import Depends, Request

from app.config import Settings
from app.db.base import Connection, Database


def create_database(settings: Settings) -> Database:
    if settings.db_backend == "hana":
        from app.db.hana import HanaDatabase

        return HanaDatabase(settings)

    from app.db.sqlite import SQLiteDatabase

    return SQLiteDatabase(settings.sqlite_path)


def get_connection(request: Request) -> Iterator[Connection]:
    """One connection per request; commits on success, rolls back on error."""
    database: Database = request.app.state.database
    conn = database.connect()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


DbConn = Annotated[Connection, Depends(get_connection)]
