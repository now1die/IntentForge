"""Regression checks for every new precision gate and the opt-in API."""
import os

import pytest
from fastapi.testclient import TestClient

from ai.behavior_oracle import program_identity
from ai.intention_engine import analyze_intention
from backend.app.main import app
from benchmarks.phase55_audit import audit
from benchmarks.phase55_evaluate import transformed

MIXED = "int f(int x,int y,int z,int rebate){int total=0;total+=x;total+=y;total+=z;total-=rebate;return total;}"
EXIT = "int f(int n){int clock=0;int marker=0;for(int i=1;i<n;clock++){marker=i;break;}return marker;}"
LOOP_DEFECT = EXIT.replace("marker=i;break;", "marker+=i;")
DEAD = "int f(){int a[3];a[2]=7;if(false){return a[3];}return a[2];}"
EDGE = DEAD.replace("false", "true")
ROUTE = "int d(int a,int b){return b-a;}int f(int p,int q){return d(p,q)+d(q,p)+d(p,q);}"
SYMMETRIC = ROUTE.replace("return b-a", "return b+a")


@pytest.mark.parametrize(("source", "category", "reason"), [
    (MIXED, "ACCUMULATOR_CONSISTENCY", "MISSING_SIGN_REQUIREMENT"),
    (EXIT, "LOOP_PROGRESS_BINDING", "LOOP_EXITS_BEFORE_UPDATE"),
    (DEAD, "FIXED_ARRAY_EDGE", "UNREACHABLE_ACCESS"),
    (SYMMETRIC, "ARGUMENT_ROLE_PERMUTATION", "SYMMETRIC_CALLEE"),
    (ROUTE.replace("+d(q,p)+", "+2*d(q,p)+"), "ARGUMENT_ROLE_PERMUTATION", "DISTINCT_CALL_CONTEXT"),
])
def test_hard_negatives_preserve_counter_evidence(source, category, reason):
    original = analyze_intention(source, phase5=True)
    current = analyze_intention(source, phase55=True)
    assert category in {row["category"] for row in original.structural_scan["findings"]}
    assert category not in {row["category"] for row in current.structural_scan["findings"]}
    withheld = next(row for row in current.structural_scan["withheld"] if row["category"] == category)
    assert withheld["counter_evidence"]["kind"] == reason and withheld["counter_evidence"]["span"]
    assert all(item.proposal.category != category for item in current.candidates)


@pytest.mark.parametrize(("source", "category", "edits"), [
    (ROUTE, "ARGUMENT_ROLE_PERMUTATION", 2),
    (LOOP_DEFECT, "LOOP_PROGRESS_BINDING", 1),
    (EDGE, "FIXED_ARRAY_EDGE", 1),
    (EXIT.replace("marker=i;break;", "if(n>0){continue;}return marker;"), "LOOP_PROGRESS_BINDING", 1),
])
def test_supported_positives_still_compile(source, category, edits):
    result = analyze_intention(source, phase55=True)
    candidate = next(item for item in result.candidates if item.proposal.category == category)
    assert candidate.compiler_valid and len(candidate.proposal.edits) == edits
    assert candidate.to_dict(source, False)["safety"]["requires_review"]


def test_possibly_wrong_mixed_sign_deliberately_abstains():
    # The same source could represent a defect under an all-positive specification.
    source = MIXED
    assert any(item.proposal.category == "ACCUMULATOR_CONSISTENCY"
               for item in analyze_intention(source, phase5=True).candidates)
    assert not analyze_intention(source, phase55=True).candidates


def test_freeze_leakage_audit_and_pure_transformations():
    admitted, report = audit()
    assert len(admitted) == 52 and sum(row["partition"] == "final" for row in admitted) == 40
    assert {"optional-view", "antenna-displacement"} <= set(report["quarantined_families"])
    for _, source, _ in transformed(ROUTE):
        assert analyze_intention(source, phase55=True).context.compiler_valid


def test_precision_api_is_opt_in():
    client = TestClient(app)
    payload = {"mode": "code_only", "code": MIXED}
    legacy = client.post("/v1/intention-analysis", json={**payload, "engine_version": 5}).json()
    current = client.post("/v1/intention-analysis", json={**payload, "engine_version": 55}).json()
    assert "withheld" not in legacy["structural_scan"]
    assert current["structural_scan"]["withheld"] and current["source_fingerprint"] == program_identity(MIXED)
    assert current["ranking"] == "V55_DETERMINISTIC"


def test_precision_behavior_reuses_worker_and_never_accepts_client_evidence(monkeypatch):
    path = "/v1/behavioral-verification"
    payload = {"source": "int f(int a,int b){return missing;}", "entry_point": "f", "engine_version": 55,
               "compare_candidates": True, "vectors": []}
    with TestClient(app, base_url="http://127.0.0.1:8000", client=("127.0.0.1", 35000)) as client:
        assert client.post(path, json={**payload, "review_order": []}).status_code == 422
        if os.getenv("INTENTFORGE_VM_SOCKET"):
            reply = client.post(path, json=payload).json()
            assert reply["availability"]["status"] == "available" and reply["requires_approval"]
            assert reply["comparison_status"] is None and any(row["new_pairs"] for row in reply["probes"])
            assert all("expected" not in row for row in reply["probes"])
        monkeypatch.delenv("INTENTFORGE_VM_GATEWAY", raising=False)
        assert client.post(path, json=payload).json()["availability"]["status"] == "disabled"
