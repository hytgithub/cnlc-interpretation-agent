"""路由拆分后的数据范围、产物查询和前端回退契约。"""

import pytest
from cnlc_agent.api.frontend import register_frontend
from cnlc_agent.app import build_app
from fastapi import FastAPI
from fastapi.testclient import TestClient
from test_service import bootstrap, select


@pytest.fixture
def business_client(tmp_path):
    with TestClient(build_app(tmp_path), headers={"X-User-ID": "owner"}) as client:
        agent, session, _ = bootstrap(client)
        assert select(client, agent, session).status_code == 200
        yield client, agent, session


def test_raw_curve_query_preserves_nulls_and_both_range_ends(business_client):
    client, agent, session = business_client
    path = f"/business/sessions/{session}/curves"
    params = {"agent_id": agent, "curve_name": "GR"}
    full = client.get(path, params=params)
    assert full.status_code == 200
    points = full.json()["curves"]["GR"]["points"]
    assert len(points) == 1201
    assert sum(p["value"] is None for p in points) == 4
    narrow = client.get(
        path, params={**params, "top_depth_m": 2000, "bottom_depth_m": 2001}
    )
    assert narrow.status_code == 200
    points = narrow.json()["curves"]["GR"]["points"]
    assert len(points) == 11
    assert points[0]["depth_m"] == 2000
    assert points[-1]["depth_m"] == 2001
    assert client.get(path, params={**params, "top_depth_m": 2000}).status_code == 422
    missing = client.get(path, params={**params, "curve_name": "UNKNOWN_CURVE"})
    assert missing.status_code == 422
    assert missing.json()["code"] == "CURVE_NOT_FOUND"


def test_http_run_results_report_and_comparison_share_session(business_client):
    client, agent, session = business_client
    base = f"/business/sessions/{session}"
    params = {"agent_id": agent}
    submitted = client.post(
        base + "/interpretation-runs",
        params=params,
        json={"expected_selection_revision": 1, "scenario_id": "baseline"},
    )
    assert submitted.status_code == 200
    run = client.get(
        base + "/interpretation-runs/" + submitted.json()["run_id"], params=params
    ).json()
    assert run["status"] == "SUCCESS"
    result_id = run["result_revision_id"]
    report = client.get(base + "/reports/" + run["report_revision_id"], params=params)
    assert report.json()["result_revision_id"] == result_id
    comparison = client.post(
        base + "/comparisons",
        params=params,
        json={
            "left_result_revision_id": result_id,
            "right_result_revision_id": result_id,
        },
    )
    assert comparison.status_code == 200
    assert comparison.json()["changes"] == []
    denied = client.get(
        base + "/results/" + result_id, params=params, headers={"X-User-ID": "other"}
    )
    assert denied.status_code == 404


def test_frontend_preserves_missing_build_and_deleted_workbench(tmp_path):
    app = FastAPI()
    register_frontend(app, tmp_path)
    with TestClient(app) as client:
        assert client.get("/").status_code == 503
        assert client.get("/workbench").status_code == 404
    (tmp_path / "index.html").write_text("<html>React shell</html>")
    app = FastAPI()
    register_frontend(app, tmp_path)
    with TestClient(app) as client:
        assert client.get("/").text == "<html>React shell</html>"
        assert client.get("/chat/agent/session").status_code == 200
        assert client.get("/workbench").status_code == 404
        assert client.get("/unknown").status_code == 404
