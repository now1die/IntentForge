"""Phase 8.5 projection, abstention and the unchanged approval boundary."""
import os

import pytest

from ai.behavior_oracle import Status, program_identity
from ai.intention_context import Example
from ai.intention_engine import analyze_intention
from ai.intention_phase85 import CATEGORIES, MAX_LOOP_POINTS, MAX_PAIR_TRIALS
from execution_service.contracts import Batch
from tests.test_phase8 import URL, client, observations

BRANCH = """int f(int n) {
  int out=n+7;
  if(n<=4) { int n=9; out=3*n; }
  return out;
}"""
PAIR = "int f(int x,int y) { return 4*x + 8*y; }"
PAIR_ROWS = (((1,0),3), ((0,1),7), ((2,3),27), ((-4,5),23))
LOOP = "int f(int n){int count=0;for(int i=0;i<=n;i++){if(i%3==0){count++;}}return count;}"


def analyze(source, rows, **settings):
    return analyze_intention(source, phase85=True, phase6_entry="f",
                             phase6_examples=tuple(Example(args, expected) for args, expected in rows), **settings)


def new_candidates(result):
    return [c for c in result.candidates if c.proposal.category in CATEGORIES]


def assert_verified(candidate, rows):
    assert candidate.compiler_valid
    assert observations(candidate.proposed_code, rows).status == Status.MATCHES_SUPPLIED_TESTS


def test_joined_paths_respect_shadowing_and_report_original_coordinates():
    rows = (((2,),27), ((3,),27), ((4,),11), ((5,),12))
    result = analyze(BRANCH, rows)
    report = result.program_analysis["phase85"]
    witness = report["branch"]
    assert witness["guards"][0]["supplied_coverage"] == {"true":3, "false":1}
    assert {row["definitions"][0]["span"]["start"]["line"] for row in witness["returns"]} == {2,3}
    assert {row["span"]["start"]["line"] for row in witness["returns"]} == {4}
    candidate = next(c for c in new_candidates(result) if "if(n<4)" in c.proposed_code)
    assert_verified(candidate, rows)
    assert_verified(candidate, (((-1,),27), ((33,),40)))
    assert report["witnesses"][0]["branch"]["guards"][0]["supplied_coverage"] == {"true":2, "false":2}


def test_boolean_short_circuit_and_interval_edits_preserve_grouping():
    source = "bool f(int lo,int x,int hi){return x>=lo && (x<hi || x==20);}"
    rows = (((0,-1,3),False), ((0,6,3),False), ((0,1,3),True), ((0,3,3),True), ((0,20,3),True))
    result = analyze(source, rows)
    choice = next(c for c in new_candidates(result) if "x<=hi" in c.proposed_code)
    assert_verified(choice, rows)
    source = "int f(int q){if(q!=0 && 12/q>2){return 8;}return 4;}"
    rows = (((0,),4), ((1,),6), ((3,),6), ((8,),4))
    for choice in new_candidates(analyze(source, rows)):
        assert_verified(choice, rows)
    result = analyze(source, rows)
    assert any("return 6;" in c.proposed_code for c in new_candidates(result))
    assert result.program_analysis["phase85"]["scope"] == "SUPPLIED_EXAMPLES_ONLY"


def test_repair_conjunction_respects_precedence():
    source = "bool f(int x){return x<0 || x>7 && x>10;}"
    rows = tuple(((x,), x<0 or x>7) for x in (-3,2,5,9,10,14))
    result = analyze(source, rows)
    assert any(c.proposal.category=="BOOLEAN_INTERVAL_CONSTRAINT" for c in new_candidates(result))
    for choice in new_candidates(result):
        assert_verified(choice, rows)


def test_coordinated_sites_are_atomic_disjoint_and_require_independent_rows():
    result = analyze(PAIR, PAIR_ROWS)
    candidate, = new_candidates(result)
    assert candidate.proposal.category == "COORDINATED_COEFFICIENTS"
    assert_verified(candidate, PAIR_ROWS + (((9,6),69),))
    rendered, = [row for row in result.to_dict()["candidates"] if row["id"]==candidate.id]
    assert rendered["source_snapshot"] == program_identity(PAIR)
    assert rendered["requires_approval"] and rendered["evidence_basis"] == "supplied_examples"
    assert [e["original"] for e in rendered["edits"]] == ["4","8"]
    assert rendered["edits"][0]["span"]["end"]["offset"] < rendered["edits"][1]["span"]["start"]["offset"]
    report = result.program_analysis["phase85"]
    assert 0 < report["pair_trials"] <= MAX_PAIR_TRIALS and report["single_trials"] > 0
    assert not new_candidates(analyze(PAIR, PAIR_ROWS[:2]))
    assert not new_candidates(analyze(PAIR, (((1,1),10), ((2,2),20), ((3,3),30))))
    assert not new_candidates(analyze(PAIR, tuple((args,3*args[0]+8*args[1]) for args,_ in PAIR_ROWS)))


def test_loop_witness_bound_and_alternate_correct_controls():
    rows = (((0,),0), ((3,),1), ((4,),2), ((6,),2))
    result = analyze(LOOP, rows)
    choice = next(c for c in new_candidates(result) if "i<n" in c.proposed_code)
    assert_verified(choice, rows + (((9,),3), ((13,),5)))
    report = result.program_analysis["phase85"]
    assert report["loop"]["iterations"] == [1,4,5,7]
    assert report["loop"]["point_limit"] == MAX_LOOP_POINTS
    assert not new_candidates(analyze(choice.proposed_code, rows))
    descending = "int f(int n){int cost=4;for(int i=n;i>=0;i-=3){cost-=2;}return cost;}"
    values = tuple(((n,),4-2*len(range(n,-1,-3))) for n in (-1,0,2,3,7))
    assert analyze(descending, values).program_analysis["phase85"]["status"] == "CONSTRAINTS_ALREADY_AGREE"
    bigger = analyze(LOOP, rows + (((70,),24),))
    assert bigger.program_analysis["phase85"]["status"] == "ANALYSIS_LIMITED"
    assert not new_candidates(bigger)


@pytest.mark.parametrize(("source", "expected_status"), [
    ("int h(int x){return x;}int f(int x){if(h(x)>1){return 4;}return 7;}", "UNSUPPORTED_PROJECTION"),
    ("int f(int x){int a[2];if(x>1){a[0]=4;}return 7;}", "UNSUPPORTED_PROJECTION"),
    ("int g=0;int f(int x){if(x>1){g=4;}return 7;}", "UNSUPPORTED_PROJECTION"),
    ("int f(int x){if(x>0){int y=x/0;return y;}return 7;}", "UNSUPPORTED_CHECKED_ARITHMETIC"),
    ("int f(int x){int z=0;for(int i=0;i<x;i++){for(int j=0;j<x;j++){z++;}}return z;}", "UNSUPPORTED_PROJECTION"),
    ("int f(int x){int z=0;for(int i=2147483646;i<=x;i++){z++;}return z;}", "UNSUPPORTED_CHECKED_ARITHMETIC"),
])
def test_abstention_coverage(source, expected_status):
    result = analyze(source, (((2,),1), ((2147483647,),3)))
    assert result.program_analysis["phase85"]["status"] == expected_status
    assert not new_candidates(result)


def test_path_explosion_and_unsampled_paths():
    branches = "".join(f"if(x<{i}){{a=1;}}else{{a=2;}}" for i in range(5))
    result = analyze(f"int f(int x){{int a=0;{branches}return a;}}", (((0,),1), ((2,),2)))
    assert result.program_analysis["phase85"]["status"] == "ANALYSIS_LIMITED"
    result = analyze(BRANCH, (((0,),27), ((2,),27)))
    assert result.program_analysis["phase85"]["branch"]["guards"][0]["supplied_coverage"]["false"] == 0
    assert not new_candidates(result)


def test_public_profile_is_opt_in_and_preserves_typed_domain_and_worker_contract():
    payload = {"code":PAIR, "mode":"examples","requirement":{"function":"f","examples":[
        {"args":list(args),"expected_return":out} for args,out in PAIR_ROWS]}}
    with client() as http:
        old = http.post("/v1/intention-analysis",json=payload | {"engine_version":8}).json()
        assert "phase85" not in old["program_analysis"]
        new = http.post("/v1/intention-analysis", json=payload | {"engine_version":85,
            "input_domain":[None,None],"partial_inputs":[[1,2]]})
        assert new.status_code == 200, new.text
        assert new.json()["program_analysis"]["phase8"]["specification"]["partial_inputs"] == 1
        assert new.json()["candidates"][0]["hypothesis_origin"] == "phase85"
        invalid = http.post("/v1/intention-analysis", json=payload | {"engine_version":85,
            "input_domain":[{"minimum":0,"maximum":2},None]})
        assert invalid.status_code == 422
    assert 85 not in Batch.model_json_schema()["properties"]["engine_version"]["enum"]


@pytest.mark.skipif(not os.getenv("INTENTFORGE_VM_SOCKET"), reason="Requires the restricted Linux worker")
def test_isolated_worker_verifies_atomic_candidate_and_rejects_hostile_requests():
    payload = {"engine_version":85,"source":PAIR,"entry_point":"f","compare_candidates":True,
               "vectors":[{"arguments":args,"expected":out} for args,out in PAIR_ROWS]}
    with client() as http:
        reply = http.post(URL, json=payload)
        assert reply.status_code == 200, reply.text
        verified = reply.json()
        assert verified["availability"]["status"] == "available" and verified["requires_approval"]
        assert verified["guided_evidence"]["confirmed_fault"] and verified["program"] == program_identity(PAIR)
        ident = verified["guided_evidence"]["recommended_candidate"]
        assert verified["candidate_categories"][ident] == "COORDINATED_COEFFICIENTS"
        assert len(verified["candidate_details"][ident]["edits"]) == 2
        assert verified["specification"]["phase85"]["mode"] == "coordinated"
        for invalid in ({"language":"c"}, {"programs":[]}, {"limits":{"steps":50000}}, {"candidate_id":ident}):
            assert http.post(URL,json=payload|invalid).status_code == 422
