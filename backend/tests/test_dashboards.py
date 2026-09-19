BAR_SPEC = {
    "query": {"dataset": "items", "dimensions": [{"field": "category"}], "measures": ["item_count"]},
    "chart": {"type": "bar"},
}
KPI_SPEC = {"query": {"dataset": "items", "measures": ["total_quantity"]}, "chart": {"type": "kpi"}}


def first_dashboard(client) -> dict:
    [dashboard] = client.get("/api/dashboards").json()
    return client.get(f"/api/dashboards/{dashboard['id']}").json()


def test_first_visit_gets_a_default_dashboard(client):
    dashboard = first_dashboard(client)
    assert dashboard["name"] == "My dashboard"
    [widget] = dashboard["widgets"]
    assert widget["spec"]["query"]["measures"] == ["total_quantity"]
    # Listing again doesn't add another
    assert len(client.get("/api/dashboards").json()) == 1


def test_dashboard_and_widget_crud(client):
    dash = client.post("/api/dashboards", json={"name": "Warehouse"}).json()
    base = f"/api/dashboards/{dash['id']}"

    bar = client.post(f"{base}/widgets", json={"title": "Items per category", "spec": BAR_SPEC})
    assert bar.status_code == 201
    bar = bar.json()
    assert (bar["x"], bar["y"], bar["w"], bar["h"]) == (0, 0, 6, 8)

    kpi = client.post(f"{base}/widgets", json={"spec": KPI_SPEC}).json()
    assert (kpi["y"], kpi["w"], kpi["h"]) == (8, 4, 4)  # below the bar, KPI-sized

    data = client.get(f"/api/widgets/{bar['id']}/data").json()
    assert data["title"] == "Items per category"
    assert data["chart_type"] == "bar"
    assert data["rows"][0] == {"category": "Hardware", "item_count": 3}
    assert client.get(f"/api/widgets/{kpi['id']}/data").json()["rows"] == [{"total_quantity": 5149}]

    res = client.put(f"{base}/layout", json=[{"id": kpi["id"], "x": 6, "y": 0, "w": 6, "h": 8}])
    assert res.status_code == 204
    widgets = {w["id"]: w for w in client.get(base).json()["widgets"]}
    assert (widgets[kpi["id"]]["x"], widgets[kpi["id"]]["w"]) == (6, 6)
    assert widgets[bar["id"]]["x"] == 0  # untouched

    donut = {**BAR_SPEC, "chart": {"type": "donut"}}
    updated = client.patch(f"/api/widgets/{bar['id']}", json={"spec": donut}).json()
    assert updated["spec"]["chart"]["type"] == "donut"
    assert updated["title"] == "Items per category"

    assert client.patch(base, json={"name": "Yard"}).json()["name"] == "Yard"
    assert client.delete(f"/api/widgets/{kpi['id']}").status_code == 204
    assert len(client.get(base).json()["widgets"]) == 1

    assert client.delete(base).status_code == 204
    assert client.get(base).status_code == 404
    assert client.get(f"/api/widgets/{bar['id']}/data").status_code == 404


def test_other_users_cannot_see_or_touch_dashboards(make_client):
    alice = make_client("alice")
    bob = make_client("bob")
    dash = first_dashboard(alice)
    widget_id = dash["widgets"][0]["id"]
    base = f"/api/dashboards/{dash['id']}"

    assert dash["id"] not in [d["id"] for d in bob.get("/api/dashboards").json()]
    assert bob.get(base).status_code == 404
    assert bob.patch(base, json={"name": "mine now"}).status_code == 404
    assert bob.delete(base).status_code == 404
    assert bob.post(f"{base}/widgets", json={"spec": BAR_SPEC}).status_code == 404
    assert bob.put(f"{base}/layout", json=[]).status_code == 404
    assert bob.get(f"/api/widgets/{widget_id}/data").status_code == 404
    assert bob.patch(f"/api/widgets/{widget_id}", json={"title": "x"}).status_code == 404
    assert bob.delete(f"/api/widgets/{widget_id}").status_code == 404

    # Bob can't move Alice's widget by listing it in his own dashboard's layout
    bobs = first_dashboard(bob)
    bob.put(f"/api/dashboards/{bobs['id']}/layout", json=[{"id": widget_id, "x": 9, "y": 9, "w": 3, "h": 3}])
    assert first_dashboard(alice)["widgets"][0]["x"] == 0
    assert first_dashboard(alice)["name"] == "My dashboard"


def test_invalid_spec_is_rejected(client):
    dash = first_dashboard(client)
    bad = {"query": {"dataset": "items"}, "chart": {"type": "sparkles"}}
    assert client.post(f"/api/dashboards/{dash['id']}/widgets", json={"spec": bad}).status_code == 422
