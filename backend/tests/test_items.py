from app.config import Settings

SEEDED_ITEMS = 8  # rows inserted by migration 0002_seed_items


def test_health(anon_client):
    res = anon_client.get("/api/health")
    assert res.status_code == 200
    assert res.json() == {"status": "ok", "database": "sqlite (up)"}


def test_item_crud(client):
    assert len(client.get("/api/items").json()) == SEEDED_ITEMS

    res = client.post("/api/items", json={"name": "Widget", "category": "Tools", "quantity": 3})
    assert res.status_code == 201
    item = res.json()
    assert item["name"] == "Widget"
    assert item["created_at"]
    assert client.get("/api/items").json()[-1] == item

    res = client.patch(f"/api/items/{item['id']}", json={"quantity": 5})
    assert res.json()["quantity"] == 5
    assert res.json()["name"] == "Widget"

    assert client.delete(f"/api/items/{item['id']}").status_code == 204
    assert client.get(f"/api/items/{item['id']}").status_code == 404


def test_totals_and_chart(client):
    totals = client.get("/api/items/totals").json()
    assert {t["category"] for t in totals} == {"Hardware", "Electrical", "Safety", "Consumables"}
    assert totals[0] == {"category": "Hardware", "total_quantity": 4150, "item_count": 3}

    fig = client.get("/api/items/charts/quantity-by-category").json()
    assert fig["data"][0]["type"] == "bar"
    assert fig["layout"]["title"]["text"] == "Quantity by category"


def test_hana_url_is_built_without_leaking_the_password():
    settings = Settings(db_backend="hana", hana_user="ME", hana_password="p@ss/word", hana_schema="FIELDOPS")
    url = settings.database_url()
    assert url.drivername == "hana+hdbcli"
    assert url.password == "p@ss/word"  # kept intact, escaping is SQLAlchemy's job
    assert url.query["currentSchema"] == "FIELDOPS"
    assert "p@ss" not in url.render_as_string(hide_password=True)


def test_sqlite_url_points_at_the_configured_file(tmp_path):
    url = Settings(sqlite_path=tmp_path / "x.db").database_url()
    assert url.drivername == "sqlite"
    assert url.database == str(tmp_path / "x.db")
