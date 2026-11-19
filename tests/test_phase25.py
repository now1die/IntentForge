"""Regression checks for the expanded source-evidence path and API modes."""

import json

import joblib
import pytest
from fastapi.testclient import TestClient

from ai.correction_safety import repair_key
from ai.intention_context import Requirement
from ai.intention_engine import analyze_intention
from ai.intention_learning import MODEL_PATH, load_expanded_ranker
from backend.app.main import app
from benchmarks.phase25_audit import Source, check
from benchmarks.phase25_data import DEVELOPMENT, generate
from benchmarks.train_phase25 import train


@pytest.mark.parametrize("source,expected,category", [
    ("int f(int a,int b){int total=a*b;return a+b;}",
     "int f(int a,int b){int total=a*b;return total;}", "RETURN_EXPRESSION"),
    ("int f(int a,int b,int c,int d,int e,int g){int x=a+b;int y=c+d;int z=e-g;return x+y+z;}",
     "int f(int a,int b,int c,int d,int e,int g){int x=a+b;int y=c+d;int z=e+g;return x+y+z;}", "ARITHMETIC_OPERATOR"),
    ("int f(int a,int b,int c){int hits=0;if(a>=8){hits++;}if(b>=8){hits++;}if(c>8){hits++;}return hits;}",
     "int f(int a,int b,int c){int hits=0;if(a>=8){hits++;}if(b>=8){hits++;}if(c>=8){hits++;}return hits;}", "COMPARISON_OPERATOR"),
    ("int v[7];int f(){return v[6]+v[7];}", "int v[7];int f(){return v[6]+v[6];}", "ARRAY_INDEX"),
    ("int g(int x,int y){return x-y;} int f(int a,int b){g(a,b);g(a,b);return g(b,a);}",
     "int g(int x,int y){return x-y;} int f(int a,int b){g(a,b);g(a,b);return g(a,b);}", "FUNCTION_ARGUMENT"),
    ("bool gate(bool enabled,int limit){return enabled&&limit>0;} bool entry(bool live,int size){return gate(size);}",
     "bool gate(bool enabled,int limit){return enabled&&limit>0;} bool entry(bool live,int size){return gate(live,size);}", "FUNCTION_ARGUMENT"),
])
def test_code_only_repairs_are_anchored_and_reviewable(source, expected, category):
    result = analyze_intention(source, enhanced=True)
    matches = [row for row in result.candidates if repair_key(row.proposed_code) == repair_key(expected)]
    assert matches and matches[0].proposal.category == category and matches[0].compiler_valid
    assert all(candidate["safety"]["requires_review"] for candidate in result.to_dict()["candidates"])
    assert result.decision != "STRONG_SPECIFICATION_EVIDENCE"
    assert result.context.source == source


def test_names_and_incompatible_analogies_produce_no_proposal():
    for source in (
        "int add(int l,int r){return l-r;}",
        "int f(int a,int b,int c){int n=0;if(a>4){n++;}if(b>4){n++;}if(c<4){n+=9;}return n;}",
        "int f(int a,int b){int computed=a*b;return 2;}",
        "int a[3];int f(){return a[3];}",
    ):
        result = analyze_intention(source, enhanced=True)
        assert not result.candidates


@pytest.mark.parametrize("source,description,expression", [
    ("int f(int x,int y){if(x>y)return x;return y;}", "Return the minimum of x and y", "x < y"),
    ("bool f(int x){return x<9;}", "Return whether x is between 2 and 8 inclusive", "x >= 2 && x <= 8"),
    ("bool f(bool ready,int jobs){return ready;}", "Return whether both ready and jobs is at least 2", "(ready) && (jobs >= 2)"),
    ("int f(int x){return x-4;}", "Return x incremented by 4", "x + (4)"),
    ("int combine(int a,int b){return a-b;}int f(int x){return combine(3,x);}",
     "Return the result of calling combine with x and 3", "combine(x, 3)"),
])
def test_description_grammar_builds_a_bounded_requirement(source, description, expression):
    subject = "f" if "combine" in source else None
    result = analyze_intention(source, Requirement(function=subject, description=description), enhanced=True)
    assert result.requirement_status == "SUPPORTED"
    assert result.candidates and expression in result.candidates[0].proposed_code


def test_natural_mode_abstains_and_api_separates_input_modalities():
    code = "int f(int n){return n/2;}"
    with TestClient(app) as client:
        legacy = client.post("/v1/intention-analysis", json={"code": code})
        textual = client.post("/v1/intention-analysis", json={
            "code": code, "mode": "natural_language", "requirement": {"description": "Return n * 2"},
        })
        mixed = client.post("/v1/intention-analysis", json={
            "code": code, "mode": "natural_language", "requirement": {"description": "Make this faster", "return_expression": "n*2"},
        })
    assert legacy.status_code == 200 and legacy.json()["requirement_status"] is None
    assert textual.status_code == 200 and textual.json()["requirement_status"] == "UNSUPPORTED_DESCRIPTION"
    assert textual.json()["candidates"] == []
    assert mixed.status_code == 422


def test_matching_requirement_suppresses_unrelated_code_only_hypothesis():
    source = "int f(int x,int y){int computed=x*y;return x;}"
    assert analyze_intention(source, enhanced=True).candidates
    agreed = analyze_intention(source, Requirement(return_expression="x"), enhanced=True)
    assert agreed.decision == "REQUIREMENT_SHAPE_MATCHES" and not agreed.candidates


def test_multiple_edits_and_inference_budget():
    source = "int f(int start,int limit){int state=statr;return limt+state;}"
    result = analyze_intention(source, enhanced=True)
    assert any(candidate.proposal.category == "MULTIPLE_LOCALIZED" and candidate.compiler_valid for candidate in result.candidates)
    bounded = analyze_intention(source, enhanced=True, candidate_budget=2)
    assert bounded.attempts <= 2
    timeout = analyze_intention(source, enhanced=True, budget_seconds=0)
    assert timeout.decision == "BUDGET_EXHAUSTED" and timeout.attempts == 0


def test_artifact_compatibility_and_category_local_scores(tmp_path):
    ranker, mode = load_expanded_ranker()
    assert ranker and len(ranker.selected) >= 2
    incompatible = tmp_path / "wrong.joblib"
    joblib.dump({"feature_version": 0, "models": {}, "selected": {}}, incompatible)
    assert load_expanded_ranker(incompatible) == (None, "EXPANDED_ARTIFACT_INCOMPATIBLE")
    assert load_expanded_ranker(tmp_path / "absent.joblib") == (None, "EXPANDED_ARTIFACT_UNAVAILABLE")
    fixtures = [case for case in generate()["cases"] if case["split"] == "validation" and case["category"] in ranker.selected]
    active = set()
    for case in fixtures:
        learned = analyze_intention(case["source"], enhanced=True, expanded_ranker=ranker, ranking_status=mode)
        deterministic = analyze_intention(case["source"], enhanced=True)
        assert {c.id for c in learned.candidates} == {c.id for c in deterministic.candidates}
        active.update(c.proposal.category for c in learned.candidates if c.relative_score is not None)
    assert len(active) >= 2 and active <= ranker.selected.keys()


def test_training_reproduction_and_calibrated_scores_are_offline_only():
    data = json.loads(DEVELOPMENT.read_text())
    assert data == generate()
    _, trained = train(data)
    archived = json.loads((DEVELOPMENT.parent.parent / "reports" / "phase25-training-v1.json").read_text())
    assert trained["selected"] == archived["selected"]
    assert trained["validation"] == archived["validation"]
    assert trained["calibration"] == archived["calibration"]
    assert not trained["calibration"]["pooled_exploratory"]["exposed_probabilities"]


def test_split_checker_rejects_renamed_historical_templates():
    same_shape = "int renamed(int arg){return arg*2;}"
    result = check([{"id": "train", "family": "f", "split": "train", "source": same_shape, "accepted": []}], [],
                   historical=[Source("int old(int age){return age*3;}", "hist", "historical")], check_near=False)
    assert any("tokens" in error for error in result["issues"])
    assert any("AST" in error for error in result["issues"])
