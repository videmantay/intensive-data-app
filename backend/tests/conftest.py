"""Shared fixtures. Every test gets a fresh SQLite file, migrated at startup.

Most endpoints need a signed-in user, so `client` is signed in as "alice".
`make_client` builds more clients: a second user, or custom settings.
"""

from contextlib import ExitStack

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session

from app.auth import service as auth_service
from app.config import Settings
from app.main import create_app

PASSWORD = "correct horse battery staple"


def sign_in(client: TestClient, username: str) -> None:
    """Create `username` (if needed) and sign `client` in as them."""
    with Session(client.app.state.engine) as session:
        if auth_service.get_user_by_username(session, username) is None:
            auth_service.create_user(session, username, PASSWORD)
            session.commit()
    res = client.post("/api/auth/login", json={"username": username, "password": PASSWORD})
    assert res.status_code == 200, res.text


@pytest.fixture
def make_client(tmp_path):
    """`make_client(username="bob", **settings)`; all clients share one database."""
    with ExitStack() as stack:

        def make(username: str | None = "alice", **settings_kwargs) -> TestClient:
            app = create_app(Settings(sqlite_path=tmp_path / "test.db", **settings_kwargs))
            client = stack.enter_context(TestClient(app))
            if username:
                sign_in(client, username)
            return client

        yield make


@pytest.fixture
def client(make_client) -> TestClient:
    return make_client()


@pytest.fixture
def anon_client(make_client) -> TestClient:
    return make_client(username=None)
