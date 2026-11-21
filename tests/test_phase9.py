"""Independent VM cross-checks for bounded Phase 9 evidence."""
import os

import pytest

from ai.behavior_oracle import Status, program_identity
from ai.intention_context import Example
from ai.intention_engine import analyze_intention
from ai.intention_phase9 import CATEGORIES
from execution_service.contracts import Batch
from tests.test_phase8 import URL, client, observations

VARIABLE = "int f(int a,int n,int s){int tally=0;for(int i=a;n>=i;i+=s){tally++;}return tally;}"
VARIABLE_ROWS = (((0,4,2),2), ((2,9,3),3), ((3,3,2),0), ((8,5,0),0))
MIXED = """int f(int n,int offset){
    int count=0; int credit=offset;
    for(int i=1;i<=n;i=i+1){
        if(i%3==0){count++;credit+=i;}else{credit+=2;}
    }
    return credit+count;
}"""
CROSS = "int f(int x){if(x<0){return 4*x+1;}return 8*x-2;}"
CROSS_ROWS = (((-4,),-11), ((-3,),-8), ((2,),12), ((3,),19))
RUNTIME = "int f(int a,int b){return 15/(a-b);}"
RUNTIME_ROWS = (((5,5),1), ((4,2),2), ((2,3),3))


def analysis(code, rows, **settings):
    return analyze_intention(code, phase9=True, phase6_entry="f",
                             phase6_examples=tuple(Example(x,y) for x,y in rows), **settings)


def generated(result):
    return [candidate for candidate in result.candidates if candidate.proposal.category in CATEGORIES]


def matches(result, rows):
    for candidate in generated(result):
        assert candidate.compiler_valid
        assert observations(candidate.proposed_code, rows).status == Status.MATCHES_SUPPLIED_TESTS


def test_variable_steps_reverse_guard_and_skip_latch_on_empty_interval():
    result = analysis(VARIABLE, VARIABLE_ROWS)
    model = result.program_analysis["phase9"]["loop_summary"]
    assert model["guard_reversed"] and model["variable_step"]
    assert model["steps"] == [2,3,2,None] and model["iterations"] == [3,3,1,0]
    candidate, = generated(result)
    assert "n>i" in candidate.proposed_code
    matches(result, VARIABLE_ROWS + (((-5,7,4),3),))
    assert not generated(analysis(VARIABLE, VARIABLE_ROWS + (((0,3,0),2),)))


def test_mixed_update_transfer_preserves_checked_order_and_dependencies():
    rows = tuple(((n,b),b + sum(i+1 if i%3==0 else 3 for i in range(1,n+1))) for n,b in [(0,8),(2,5),(4,-2),(7,2),(8,0)])
    result = analysis(MIXED, rows)
    assert result.program_analysis["phase9"]["loop_summary"]["carriers"][1]["name"] == "credit"
    assert len(generated(result)) >= 1
    assert any("credit+=3" in candidate.proposed_code for candidate in generated(result))
    matches(result, rows)
    correct_rows = tuple(((n,b),b + sum(i+1 if i%3==0 else 2 for i in range(1,n+1)))
                         for n,b in [(0,8),(2,5),(4,-2),(7,2)])
    assert not generated(analysis(MIXED, correct_rows))
    without_mixed = analysis(MIXED, rows, phase9_components=frozenset({"normalization"}))
    assert without_mixed.program_analysis["phase9"]["status"] == "UNSUPPORTED_PROJECTION"


@pytest.mark.parametrize("transform", [
    lambda source: source.replace("n>=i", "i<=n"),
    lambda source: source.replace("return tally;", "{int tally=7; {int tally=3;}} return tally;"),
    lambda source: source.replace("i+=s", "i=s+i"),
    lambda source: source.replace("int tally=0;", "int stride=s; {int tally=0;} int tally=0;").replace("i+=s", "i+=stride"),
])
def test_equivalent_loop_layouts_remain_eligible(transform):
    changed = transform(VARIABLE)
    old, new = (observations(code, VARIABLE_ROWS) for code in (VARIABLE,changed))
    assert [row.actual for row in old.observations] == [row.actual for row in new.observations]
    result = analysis(changed, VARIABLE_ROWS)
    assert any(c.proposal.category == "GENERALIZED_LOOP_CONSTRAINT" for c in generated(result))
    matches(result, VARIABLE_ROWS)


@pytest.mark.parametrize("code,status", [
    (VARIABLE.replace("tally++;","s--; tally++;"), "UNSUPPORTED_PROJECTION"),
    (VARIABLE.replace("tally++;","break;"), "UNSUPPORTED_PROJECTION"),
    (VARIABLE.replace("tally++;","tally++; i++;"), "UNSUPPORTED_PROJECTION"),
    (VARIABLE.replace("tally++;","for(int j=0;j<2;j++){tally++;}"), "UNSUPPORTED_PROJECTION"),
    (VARIABLE, "ANALYSIS_LIMITED"),
])
def test_unsupported_loop_shapes_abstain(code, status):
    rows = VARIABLE_ROWS[:2] + (((0,103,1),104),)
    result = analysis(code, rows)
    assert result.program_analysis["phase9"]["status"] == status
    assert not generated(result)


def test_two_path_repair_requires_both_observed_paths():
    result = analysis(CROSS, CROSS_ROWS)
    candidate, = generated(result)
    assert candidate.proposal.category == "CROSS_BRANCH_COEFFICIENTS"
    assert len(candidate.proposal.edits) == 2
    rendered, = result.to_dict()["candidates"]
    assert rendered["source_snapshot"] == program_identity(CROSS) and rendered["requires_approval"]
    for edit in rendered["edits"]:
        start, end = (edit["span"][key]["offset"] for key in ("start","end"))
        assert CROSS[start:end] == edit["original"]
    matches(result, CROSS_ROWS + (((0,),-2),((-11,),-32)))
    assert not generated(analysis(CROSS, CROSS_ROWS[:2] + (((-5,),-14),)))


def test_localized_runtime_model_requires_output_constraints_beyond_failure():
    result = analysis(RUNTIME, RUNTIME_ROWS)
    candidate, = generated(result)
    assert candidate.proposal.category == "RUNTIME_CONSTRAINT"
    assert result.program_analysis["phase9"]["modeled_faults"][0]["operands"] == [15,0]
    assert observations(RUNTIME,RUNTIME_ROWS).status == Status.BEHAVIOR_UNKNOWN
    matches(result, RUNTIME_ROWS + (((12,3),1),))
    assert not generated(analysis(RUNTIME, (((8,8),0),((5,5),1))))
    assert not generated(analysis(RUNTIME, RUNTIME_ROWS[:-1] + (((2,3),14),)))


def test_public_engine_and_strict_profile_contract():
    body = {"code":CROSS,"engine_version":9,"mode":"examples","requirement":{"function":"f","examples":[
            {"args":args,"expected_return":expected} for args,expected in CROSS_ROWS]}}
    with client() as http:
        current = http.post("/v1/intention-analysis", json=body)
        assert current.status_code == 200, current.text
        assert current.json()["candidates"][0]["hypothesis_origin"] == "phase9"
        earlier = http.post("/v1/intention-analysis", json=body | {"engine_version":85}).json()
        assert "phase9" not in earlier["program_analysis"]
    assert 9 not in Batch.model_json_schema()["properties"]["engine_version"]["enum"]


@pytest.mark.skipif(not os.getenv("INTENTFORGE_VM_SOCKET"), reason="Requires the restricted Linux worker")
def test_worker_runtime_evidence_preserves_classification_and_source_identity():
    payload = {"engine_version":9,"source":RUNTIME,"entry_point":"f","compare_candidates":True,
               "vectors":[{"arguments":args,"expected":expected} for args,expected in RUNTIME_ROWS]}
    with client() as http:
        answer = http.post(URL,json=payload)
        assert answer.status_code == 200, answer.text
        data = answer.json()
        evidence = data["runtime_observation"]
        assert data["semantic_profile"] == 9
        assert data["guided_evidence"]["original"] == "RUNTIME_FAILURE"
        assert not data["guided_evidence"]["confirmed_fault"] and data["requires_approval"]
        assert data["guided_evidence"]["recommended_candidate"] is None
        assert evidence["program"] == program_identity(RUNTIME) and evidence["input"] == [5,5]
        assert evidence["issue"]["code"] == "DIVISION_BY_ZERO" and evidence["issue"]["span"]
        assert evidence["alternatives"][data["candidates"][0]["id"]]["matched_trusted_suite"]
        assert http.post(URL,json=payload | {"runtime_observation":evidence}).status_code == 422
        assert http.post(URL,json=payload | {"language":"c"}).status_code == 422
        alone = http.post(URL,json=payload | {"compare_candidates":False}).json()
        assert alone["runtime_observation"]["input"] == [5,5] and alone["specification"] is None
        legacy = http.post(URL,json=payload | {"engine_version":85}).json()
        assert "runtime_observation" not in legacy
