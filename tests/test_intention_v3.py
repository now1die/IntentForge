from fastapi.testclient import TestClient

from ai.intention_engine import analyze_intention
from ai.intention_v3_ranker import load_generalized_ranker
from backend.app.main import app


def test_array_boundary_and_guarded_hard_negative():
    source = "int a[4]; int f(){int n=0;for(int i=0;i<=4;i++){n=a[i];}return n;}"
    result = analyze_intention(source, generalized=True)
    assert not analyze_intention(source, enhanced=True).candidates
    assert result.finding == "HEURISTIC_SUSPICION"
    assert result.candidates[0].proposed_code == source.replace("i<=4", "i<4")
    assert result.candidates[0].to_dict(source, False)["safety"]["requires_review"]
    guarded = source.replace("n=a[i];", "if(i==4){break;} n=a[i];")
    assert analyze_intention(guarded, generalized=True).finding == "NO_SUPPORTED_MISMATCH"


def test_no_diagnosis_from_unused_computed_value_alone():
    source = "int cost(int a,int b){int bill=a*b;return a;}"
    assert analyze_intention(source, enhanced=True).finding == "HEURISTIC_SUSPICION"
    assert analyze_intention(source, generalized=True).finding == "NO_SUPPORTED_MISMATCH"


def test_duplicate_guard_reports_observation_and_abstains_on_value():
    source = "int f(int a){if(a>0){return a;}else if(a>0){return -a;}return 0;}"
    result = analyze_intention(source, generalized=True)
    assert result.decision == "INSUFFICIENT_CONTEXT"
    assert result.evidence[0].kind == "DUPLICATE_GUARD"
    assert not result.candidates


def test_typed_permutation_reorders_existing_bindings_and_compiles():
    source = "int f(int a,float b,bool c){return a;} int g(int a,float b,bool c){return f(c,a,b);}"
    result = analyze_intention(source, generalized=True)
    top = result.candidates[0]
    assert top.compiler_valid and top.proposed_code == source.replace("f(c,a,b)", "f(a,b,c)")
    assert any(fact.kind == "TYPED_PERMUTATION" for fact in top.proposal.evidence)


def test_v3_requirements_and_api_replay():
    api = TestClient(app)
    payload = {"code": "bool f(int x){return x>=1 && x<=5;}", "mode": "natural_language",
               "requirement": {"description": "return whether x is between 1 and 5 exclusive"}}
    v2 = api.post("/v1/intention-analysis", json=payload).json()
    v3 = api.post("/v1/intention-analysis", json={**payload, "engine_version": 3}).json()
    assert v2["requirement_status"] == "UNSUPPORTED_DESCRIPTION"
    assert v3["requirement_status"] == "SUPPORTED"
    assert "x > 1 && x < 5" in v3["candidates"][0]["proposed_code"]


def test_artifact_and_category_fallback():
    ranker, status = load_generalized_ranker()
    assert ranker and set(ranker.models) == {"pointwise", "pairwise", "boosted"}
    assert status == "V3_DETERMINISTIC" and not ranker.selected
