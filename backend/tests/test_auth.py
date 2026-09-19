from tests.conftest import PASSWORD


def test_protected_routes_need_a_session(anon_client):
    assert anon_client.get("/api/items").status_code == 401
    assert anon_client.get("/api/auth/me").status_code == 401
    assert anon_client.get("/api/assistant/status").status_code == 401


def test_login_me_logout(client):
    me = client.get("/api/auth/me").json()
    assert me["username"] == "alice"
    assert "password_hash" not in me
    assert client.get("/api/items").status_code == 200

    assert client.post("/api/auth/logout").status_code == 204
    assert client.get("/api/auth/me").status_code == 401


def test_username_is_case_insensitive(client, anon_client):
    res = anon_client.post("/api/auth/login", json={"username": "  ALICE ", "password": PASSWORD})
    assert res.status_code == 200
    assert res.json()["username"] == "alice"


def test_wrong_password_and_unknown_user(client, anon_client):
    for username, password in [("alice", "nope"), ("nobody", PASSWORD)]:
        res = anon_client.post("/api/auth/login", json={"username": username, "password": password})
        assert res.status_code == 401
        assert res.json()["detail"] == "Wrong username or password"
    assert anon_client.get("/api/auth/me").status_code == 401


def test_tampered_cookie_is_rejected(client):
    client.cookies.set("fieldops_session", "forged")
    assert client.get("/api/auth/me").status_code == 401
