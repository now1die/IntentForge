"""Independent tests for each Phase 3.5 workstream and the common API."""
from io import BytesIO
import os

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from ai import artifact_trust
from ai.behavior_oracle import (
    BehaviorResult, ExecutionLimits, Observation, Status, Vector, program_identity,
)
from ai.intention_context import Example, Requirement
from ai.intention_engine import analyze_intention
from ai.intention_v3_ranker import load_generalized_ranker
from ai.llm_fallback import MAX_OLLAMA_BODY, OllamaFallbackService, RejectOllamaRedirect
from backend.app.main import app
from clang_backend import adapter

api = TestClient(app)
LOOP = "int data[6];int f(int a){for(int i=4;i>=-1;i--){data[i]=a; a++;}return a;}"


def test_a_counted_recovery_is_opt_in_and_review_only():
    assert not analyze_intention(LOOP, generalized=True).candidates
    result = analyze_intention(LOOP, phase35=True).to_dict()
    assert result["candidates"][0]["proposed_code"] == LOOP.replace("i>=-1", "i>-1")
    assert result["candidates"][0]["compiler_valid"]
    assert result["candidates"][0]["safety"]["requires_review"]
    hard_negative = LOOP.replace("data[i]=a;", "if(i<0){break;}data[i]=a;")
    assert not analyze_intention(hard_negative, phase35=True).candidates
    model, label = load_generalized_ranker(4)
    assert model and label == "V4_DETERMINISTIC"


def test_b_minic_span_scope_binding_and_legacy_api():
    source = "int f(int a){ /* 😀 */ int b=a+1; if(a>0){int b=7;return b;}return b;}"
    report = api.post("/v1/compiler-evidence", json={"language": "mini-c", "code": source}).json()
    assert report["schema_version"] == 1 and report["provider"] == "ply-mini-c"
    unit = report["units"][0]
    assert unit["ast"] == "available"
    identifiers = [row for row in unit["nodes"] if row["kind"] == "Identifier" and row["name"] == "b"]
    assert len({row["reference"] for row in identifiers}) == 2
    declarations = {row["id"] for row in unit["nodes"] if row["declaration"]}
    assert all(row["reference"] in declarations for row in identifiers)
    ref = identifiers[-1]["span"]["start"]
    prefix = source[: source.rindex("b")]
    assert ref["column"] == len(prefix.encode("utf-16-le")) // 2 + 1
    assert ref["byte_offset"] == len(prefix.encode())
    assert len(unit["scopes"]) >= 3 and unit["control_flow_nodes"]
    assert api.post("/analyze", json={"code": source}).json()["success"]
    syntax = api.post("/v1/compiler-evidence", json={"language": "mini-c", "code": "int f( {"}).json()
    assert syntax["units"][0]["ast"] == "unavailable" and syntax["units"][0]["diagnostics"]


def test_b_clang_files_macro_scope_and_legacy_api():
    if not os.getenv("INTENTFORGE_LIBCLANG"):
        pytest.skip("requires optional isolated libclang")
    files = {"inc/item.h": "#define VALUE 5\n", "b.c": "#include \"inc/item.h\"\nint f(void){return VALUE;}"}
    payload = {"files": files, "translation_units": ["b.c"]}
    raw = api.post("/v1/c-analysis", json=payload).json()
    shared = api.post("/v1/compiler-evidence", json={**payload, "language": "c"}).json()
    assert raw["status"] == shared["status"] == "ok"
    assert shared["units"][0]["nodes"] == raw["units"][0]["nodes"]
    assert shared["units"][0]["scopes"] and shared["units"][0]["control_flow_nodes"]
    assert any(node["kind"] == "MACRO_DEFINITION" and node["span"]["file"] == "inc/item.h"
               for node in shared["units"][0]["nodes"])
    assert "intelligent_repair" in shared["unsupported"]


def test_c_transport_and_probe_contention(monkeypatch):
    for route, payload in [("/v1/compiler-evidence", {"language": "mini-c", "code": ""}),
                           ("/v1/c-analysis", {"code": ""})]:
        assert api.post(route, json=payload, headers={"Content-Encoding": "gzip"}).status_code == 415
        assert api.post(route, content=b"x" * 640_001).status_code == 413
    monkeypatch.setenv("INTENTFORGE_CLANG_MODE", "isolated")
    monkeypatch.setenv("INTENTFORGE_LIBCLANG", str(__file__))
    adapter._discover.cache_clear()
    with adapter.PROBE_LOCK:
        assert "in progress" in adapter.capability().detail
    assert adapter.capability().status == "unavailable"


def test_c_worker_shape_failure_cleans_staging_and_releases_slot(monkeypatch, tmp_path):
    from clang_backend.contract import Capability

    locations = []
    def worker(args, home):
        locations.append(home)
        assert (home / "request.json").is_file()
        return {"status": "fabricated"}
    monkeypatch.setenv("INTENTFORGE_LIBCLANG", str(tmp_path / "libclang.so"))
    monkeypatch.setattr(adapter, "capability", lambda: Capability(status="available", detail="stub"))
    monkeypatch.setattr(adapter, "_run", worker)
    for _ in range(3):
        result = adapter.analyze({"x.c": "int x;"}, ["x.c"], "c17")
        assert result.status == "unavailable"
    assert all(not location.exists() for location in locations)


def test_c_tampered_artifact_is_rejected_before_deserialization(monkeypatch, tmp_path):
    artifact = tmp_path / "intention_ranker_v4.joblib"
    artifact.write_bytes(b"tampered")
    monkeypatch.setattr(artifact_trust.joblib, "load", lambda *args: pytest.fail("unverified artifact was opened"))
    with pytest.raises(ValueError, match="integrity"):
        artifact_trust.load_packaged_artifact(artifact)


def test_d_evidence_label_and_abstention():
    reviewed = api.post("/v1/intention-analysis", json={
        "code": LOOP, "mode": "code_only", "engine_version": 4,
    }).json()
    assert reviewed["recommendation"] == "REVIEW_WITH_EVIDENCE"
    assert reviewed["candidates"][0]["tier"] == "STRONG_CONTEXT"
    assert reviewed["candidates"][0]["relative_score"] is None
    ambiguous = api.post("/v1/intention-analysis", json={
        "code": "int f(int a,int b){return ghost;}", "mode": "code_only", "engine_version": 4,
    }).json()
    assert ambiguous["recommendation"] == "ABSTAIN"


def test_e_ollama_transport_limits_and_redirect_policy():
    service = OllamaFallbackService(opener=lambda *args, **kwargs: BytesIO(b"x" * (MAX_OLLAMA_BODY + 1)))
    assert not service.available
    with pytest.raises(ValueError, match="byte limit"):
        service._request("/api/tags", method="GET", body=None, timeout=1)
    assert RejectOllamaRedirect().redirect_request(None, None, 302, "", {}, "http://elsewhere") is None
    assert not OllamaFallbackService(timeout=float("nan")).available


def test_f_trusted_behavior_is_bound_to_candidate_and_supplied_vectors():
    vector = Vector(arguments=(1,), expected=2)
    source = "int f(int x){return x;}"
    result = analyze_intention(source, Requirement(function="f", return_expression="x+1",
                               examples=(Example((1,), 2),)), phase35=True)
    choice = result.candidates[0]
    class FixtureOracle:
        def verify(self, source, entry_point, test_vectors, limits, *, candidate_id=None):
            return BehaviorResult(program=program_identity(source), entry_point=entry_point,
                                  candidate_id=candidate_id, status=Status.MATCHES_SUPPLIED_TESTS,
                                  observations=(Observation(vector=test_vectors[0], actual=2),))
    trusted = FixtureOracle().verify(choice.proposed_code, "f", (vector,), ExecutionLimits(), candidate_id=choice.id)
    assert result.to_dict()["behavioral_status"] == "ORACLE_UNAVAILABLE"
    with pytest.raises(ValueError, match="snapshot"):
        result.record_behavior(trusted.model_copy(update={"program": program_identity(source)}))
    result.record_behavior(trusted)
    serialized = result.to_dict()["candidates"][0]
    assert serialized["behavioral_status"] == "MATCHES_SUPPLIED_TESTS"
    assert serialized["safety"]["requires_review"]
    with pytest.raises(ValidationError):
        BehaviorResult(program=trusted.program, entry_point="f", status=Status.MATCHES_SUPPLIED_TESTS,
                       observations=(Observation(vector=vector, actual=True),))
    injected = api.post("/v1/intention-analysis", json={"code": source, "behavioral_evidence": trusted.model_dump(mode="json")})
    assert injected.status_code == 422


def test_c_dedicated_service_exposes_only_clang_routes(monkeypatch):
    from backend.app.clang_service import app as isolated_app
    monkeypatch.delenv("INTENTFORGE_CLANG_MODE", raising=False)
    isolated = TestClient(isolated_app)
    assert isolated.get("/v1/c-analysis/capability").json()["status"] == "unavailable"
    assert isolated.post("/analyze", json={"code": "int f(){return 1;}"}).status_code == 404
    assert isolated.get("/health").status_code == 404
