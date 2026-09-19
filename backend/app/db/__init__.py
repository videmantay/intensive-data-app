"""Engine and session plumbing.

One SQLAlchemy engine per app, one session per request. SQLModel models describe
the tables (see `app/items/models.py`), so there is no hand-written SQL to keep in
sync between SQLite and SAP HANA.
"""

from collections.abc import Iterator
from typing import Annotated, Any

from fastapi import Depends, Request
from sqlalchemy import Engine, event, literal, select
from sqlmodel import Session, create_engine

from app.config import Settings


def create_db_engine(settings: Settings) -> Engine:
    url = settings.database_url()
    connect_args: dict[str, Any] = {}
    if settings.db_backend == "sqlite":
        # FastAPI runs sync endpoints in a threadpool, so a pooled connection can be
        # handed to a different thread than the one that opened it.
        connect_args["check_same_thread"] = False

    engine = create_engine(url, connect_args=connect_args)

    if settings.db_backend == "sqlite":

        @event.listens_for(engine, "connect")
        def _enable_foreign_keys(dbapi_conn: Any, _record: Any) -> None:
            dbapi_conn.execute("PRAGMA foreign_keys = ON")

    return engine


def ping(engine: Engine) -> bool:
    """`SELECT 1` — SQLAlchemy adds HANA's `FROM DUMMY` when it needs to."""
    with engine.connect() as conn:
        return conn.scalar(select(literal(1))) == 1


def get_session(request: Request) -> Iterator[Session]:
    """One session per request; commits on success, rolls back on error.

    `expire_on_commit=False` keeps model objects readable after the commit, so
    endpoints can return them.
    """
    engine: Engine = request.app.state.engine
    with Session(engine, expire_on_commit=False) as session:
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise


DbSession = Annotated[Session, Depends(get_session)]
