"""Login is bypassed for the demo: anonymous requests act as a built-in demo user.

Signing in still works and still scopes data to that user, which is what keeps the
ownership checks in test_dashboards.py and test_assistant.py meaningful.
"""

from sqlmodel import Session, select

from app.auth.models import User
from app.auth.service import DEMO_USERNAME
from tests.conftest import PASSWORD


def test_anonymous_requests_act_as_the_demo_user(anon_client):
    me = anon_client.get("/api/auth/me").json()
    assert me["username"] == DEMO_USERNAME
    assert "password_hash" not in me
    assert anon_client.get("/api/items").status_code == 200
    assert anon_client.get("/api/dashboards").status_code == 200


def test_the_demo_user_is_created_once(anon_client):
    for _ in range(3):
        anon_client.get("/api/dashboards")
    with Session(anon_client.app.state.engine) as session:
        demo = session.exec(select(User).where(User.username == DEMO_USERNAME)).all()
    assert len(demo) == 1
    # One demo user means one set of dashboards, not a new one per request
    assert len(anon_client.get("/api/dashboards").json()) == 1


def test_nobody_can_sign_in_as_the_demo_user(anon_client):
    for password in [PASSWORD, "demo", ""]:
        res = anon_client.post("/api/auth/login", json={"username": DEMO_USERNAME, "password": password})
        assert res.status_code in (401, 422)


def test_signing_in_still_works_and_takes_over_the_session(client):
    # `client` is signed in as alice (tests/conftest.py)
    assert client.get("/api/auth/me").json()["username"] == "alice"
    assert client.post("/api/auth/logout").status_code == 204
    # After signing out, the request falls back to the demo user instead of a 401
    assert client.get("/api/auth/me").json()["username"] == DEMO_USERNAME


def test_wrong_password_is_still_rejected(client, anon_client):
    for username, password in [("alice", "nope"), ("nobody", PASSWORD)]:
        res = anon_client.post("/api/auth/login", json={"username": username, "password": password})
        assert res.status_code == 401
        assert res.json()["detail"] == "Wrong username or password"


def test_tampered_cookie_falls_back_to_the_demo_user(client):
    client.cookies.set("fieldops_session", "forged")
    assert client.get("/api/auth/me").json()["username"] == DEMO_USERNAME
