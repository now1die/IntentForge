"""Binding-aware patterns, negative controls and bounded candidate validation."""

import pytest
from fastapi.testclient import TestClient

from ai.behavior_oracle import program_identity
from ai.intention_engine import analyze_intention
from ai.intention_phase5 import MAX_HYPOTHESES, evidence_order
from backend.app.main import app
from benchmarks.phase5_evaluate import load_audited
from benchmarks.phase5_taxonomy import historical_taxonomy

LOOP = "int f(int n){int counter=0;int total=0;for(int i=0;i<n;counter++){total+=i;}return total;}"
CALLS = "int diff(int a,int b){return b-a;}int f(int a,int b){return diff(a,b)+diff(b,a)+diff(a,b);}"
ACCUM = "int f(int a,int b,int c,int d,int e,int g){int s=1;s-=a;s+=b;s+=c;s+=d;s-=e;s+=g;return s;}"
ARRAY = "int f(int a){int item[3];item[2]=a;return item[3];}"


@pytest.mark.parametrize(("source", "category", "edits", "replacement"), [
    (LOOP, "LOOP_PROGRESS_BINDING", 1, "i++"),
    (CALLS, "ARGUMENT_ROLE_PERMUTATION", 2, "diff(a,b)+diff(a,b)+diff(a,b)"),
    (ACCUM, "ACCUMULATOR_CONSISTENCY", 2, "s += e"),
    (ARRAY, "FIXED_ARRAY_EDGE", 1, "return item[2]"),
])
def test_new_validated_candidates_use_distinct_edit_spans(source, category, edits, replacement):
    result = analyze_intention(source, phase5=True)
    finding, = result.structural_scan["findings"]
    assert finding["category"] == category and finding["evidence"]
    candidate = next(row for row in result.candidates if row.proposal.category == category)
    assert candidate.compiler_valid and replacement in candidate.proposed_code
    assert candidate.to_dict(source, False)["safety"]["requires_review"]
    spans = sorted((item.span.start.offset, item.span.end.offset) for item in candidate.proposal.edits)
    assert len(spans) == edits and all(a[1] < b[0] for a, b in zip(spans, spans[1:]))
    assert candidate.id == analyze_intention(source, phase5=True).candidates[0].id
    assert analyze_intention(source, phase5=True, phase5_generate=False).structural_scan == result.structural_scan


@pytest.mark.parametrize("source", [
    LOOP.replace("total+=i;", "total+=i;i++;"),
    LOOP.replace("total+=i;", "{int counter=9;total+=counter;}i++;"),
    CALLS.replace("diff(a,b)+diff(b,a)+diff(a,b)", "diff(a,b)+diff(b,a)"),
    CALLS.replace("diff(b,a)", "diff(b,a++)"),
    ARRAY.replace("return item[3]", "{int item[5];item[3]=a;return item[3];}"),
    ACCUM.replace("s+=b;", "s+=a;"),
])
def test_abstains_on_controls_with_incomplete_or_conflicting_evidence(source):
    assert analyze_intention(source, phase5=True).structural_scan == {"status": "HEURISTIC_SCAN", "findings": []}


def test_scanner_and_validation_share_limits():
    many = "int f(){int a[3];" + "a[3]=1;" * 35 + "return a[3];}"
    result = analyze_intention(many, phase5=True, candidate_budget=2)
    assert len(result.structural_scan["findings"]) == MAX_HYPOTHESES
    assert result.attempts <= 2 and result.structural_scan["status"] == "SCAN_LIMITED"
    assert analyze_intention(many, phase5=True, budget_seconds=0).attempts == 0
    huge = "int f(){int x=0;" + "x=x+1;" * 250 + "return x;}"
    assert analyze_intention(huge, phase5=True).structural_scan["status"] == "SCAN_LIMITED"


def test_api_opt_in_and_fixed_same_pool():
    client = TestClient(app)
    req = {"code": CALLS, "mode": "code_only"}
    legacy, current = [client.post("/v1/intention-analysis", json={**req, "engine_version": version}) for version in (4, 5)]
    assert legacy.status_code == current.status_code == 200
    assert "structural_scan" not in legacy.json() and current.json()["structural_scan"]["findings"]
    assert "source_fingerprint" not in legacy.json() and current.json()["source_fingerprint"] == program_identity(CALLS)
    pool = analyze_intention(CALLS, phase5=True).candidates
    assert {item.id for item in evidence_order(pool)} == {item.id for item in pool}


def test_frozen_families_and_historical_ids_are_auditable():
    rows, audit = load_audited()
    assert len(rows) == 25 and audit["partitions"]["final"] == 16
    assert {"v2", "v2.5", "v3", "v4", "v4_external", "phase4.5"} == {
        row["cohort"] for row in historical_taxonomy()["rows"]
    }
