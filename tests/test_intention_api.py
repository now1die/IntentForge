from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.routes import intention as route


def test_additive_endpoint_preserves_existing_analysis_response():
    code = "int f(int n){return n+n;}"
    with TestClient(app) as client:
        before = client.post("/analyze", json={"code": code}).json()
        response = client.post("/v1/intention-analysis", json={
            "code": code, "requirement": {"return_expression": "n*n"}, "include_context": True,
        })
        after = client.post("/analyze", json={"code": code}).json()
    result = response.json()
    assert response.status_code == 200 and before == after and before["success"]
    assert result["finding"] == "SPECIFICATION_SUPPORTED_SUSPICION"
    assert result["context"]["ast_status"] == "AVAILABLE"
    assert result["candidates"][0]["safety"]["requires_review"]


def test_invalid_specification_and_request_budget_are_reported():
    with TestClient(app) as client:
        assert client.post("/v1/intention-analysis", json={"code": " "*24_001}).status_code == 422
        assert client.post("/v1/intention-analysis", json={"code": "int f(){return x;}", "requirement": {
            "condition_ordinal": 1,
        }}).status_code == 422
        assert client.post("/v1/intention-analysis", json={"code": "int f(){return x;}", "requirement": {
            "return_expression": "x; x",
        }}).status_code == 422
        assert client.post("/v1/intention-analysis", json={"code": "int f(){return " + "("*70+"1"+")"*70+";}"}).status_code == 413


def test_failed_ranker_load_keeps_static_analysis_available(monkeypatch):
    monkeypatch.setattr(route, "load_ranker", lambda: (None, "ARTIFACT_UNAVAILABLE"))
    with TestClient(app) as client:
        response = client.post("/v1/intention-analysis", json={
            "code": "int f(int n){return n+n;}", "requirement": {"return_expression": "n*n"},
        })
    assert response.status_code == 200
    assert response.json()["ranking"] == "ARTIFACT_UNAVAILABLE"
    assert len(response.json()["candidates"]) == 1
