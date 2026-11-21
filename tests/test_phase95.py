"""Evidence, compiler and restricted-worker checks for engine 95."""
import os

import pytest

from ai.behavior_oracle import Status, program_identity
from ai.intention_context import Example
from ai.intention_engine import analyze_intention
from ai.intention_phase95 import CATEGORIES
from execution_service.contracts import Batch
from tests.test_phase8 import URL, client, observations

GUARD = "int f(int n){return 3*n+19;}"
GUARD_ROWS = (((-2,),7),((-1,),7),((0,),19),((4,),31))
WINDOW = """int f(int n,int a,int b,int c,int d){
    int digits[4];digits[0]=a;digits[1]=b;digits[2]=c;digits[3]=d;
    int peak=-7;
    for(int i=0;i<n-2;i++){int total=0;for(int j=0;j<2;j++){total+=digits[i+j];}
        if(total>peak){peak=total;}}
    return peak;
}"""
WINDOW_ROWS = (((2,2,3,7,5),5),((3,2,1,7,0),8),((4,5,3,6,5),11),((1,8,5,2,3),-7))
RANGE = """int f(int a,int b,int low){
  int first=low-2;
  int total=5;
  for(int i=0;i<b;i++){total+=i*a;}
  return total;
}"""
RANGE_ROWS = tuple(((a,b,l),5+a*sum(range(l-2,b))) for a,b,l in [(2,5,4),(1,8,6),(3,2,2),(4,5,1)])
HELPER = """bool eligible(int x){if(x<0){return false;}return x%3==0;}
int f(int a,int end){int found=-9;for(int i=a;i<end;i++){
  if(i==1){continue;} if(eligible(i)){found=i;break;}}return found;}"""
HELPER_ROWS = (((-2,0),0),((1,3),3),((2,8),3),((7,8),-9))


def analyze(code, rows=(), **options):
    return analyze_intention(code,phase95=True,phase6_entry="f",
                             phase6_examples=tuple(Example(args,expected) for args,expected in rows),**options)


def candidates(result, category=None):
    admitted = CATEGORIES if category is None else {category}
    return [choice for choice in result.candidates if choice.proposal.category in admitted]


def verify(choices, rows):
    assert choices
    for choice in choices:
        assert choice.compiler_valid
        assert observations(choice.proposed_code,rows).status == Status.MATCHES_SUPPLIED_TESTS


def test_guard_insertion_needs_adjacent_typed_contrast_and_is_snapshot_scoped():
    result = analyze(GUARD,GUARD_ROWS)
    choice, = candidates(result)
    assert choice.proposal.category=="DOMAIN_BASE_CASE_CONSTRAINT"
    assert "if (n < 0)" in choice.proposed_code and "return 7;" in choice.proposed_code
    verify([choice],GUARD_ROWS+(((-85,),7),((52,),175)))
    rendered = next(c for c in result.to_dict()["candidates"] if c["id"]==choice.id)
    assert rendered["requires_approval"] and rendered["source_snapshot"]==program_identity(GUARD)
    span = rendered["edits"][0]["span"]
    assert span["start"]["offset"]==span["end"]["offset"]
    assert not candidates(analyze(GUARD))
    assert not candidates(analyze(GUARD,GUARD_ROWS[:2]+GUARD_ROWS[3:]))
    assert not candidates(analyze(choice.proposed_code,GUARD_ROWS))
    assert not candidates(analyze(GUARD,GUARD_ROWS,phase95_components=frozenset({"windows"})))


def test_checked_fixed_cells_and_nested_final_window():
    result = analyze(WINDOW,WINDOW_ROWS)
    matched = candidates(result,"WINDOW_BOUNDARY_CONSTRAINT")
    verify(matched,WINDOW_ROWS+(((4,5,1,8,7),15),((0,2,3,4,5),-7)))
    assert any("i<n-1" in c.proposed_code for c in matched)
    assert any("i<=n-2" in c.proposed_code for c in matched)
    model = result.program_analysis["phase95"]
    assert any(loop["indexed_bindings"]==["digits"] for loop in model["loops"])
    assert any(loop["samples"][0]["iterations"]==0 for loop in model["loops"])
    assert all(len(c.proposal.edits)==1 for c in matched)
    unsafe = analyze(WINDOW,WINDOW_ROWS+(((7,1,2,3,4),33),))
    assert not candidates(unsafe)
    assert "INDEX_OUTSIDE_EXTENT" in unsafe.program_analysis["phase95"]["sample_issues"]


def test_range_origin_uses_reaching_scalar_and_varies_across_inputs():
    rows = RANGE_ROWS+(((2,2,3),7),)
    result = analyze(RANGE,rows)
    choice, = candidates(result,"RANGE_ORIGIN_CONSTRAINT")
    assert "int i=first;" in choice.proposed_code
    verify([choice],rows+(((5,8,5),130),))
    assert not candidates(analyze(choice.proposed_code,rows))


def test_helper_and_control_exits_use_compiler_edges_and_pure_local_state():
    result = analyze(HELPER,HELPER_ROWS)
    verify(candidates(result,"WINDOW_BOUNDARY_CONSTRAINT"),HELPER_ROWS)
    summary = result.program_analysis["phase95"]
    assert summary["helper_calls"]["eligible"]>0
    assert any(":break:" in key for key in summary["exits"])
    assert any(":continue:" in key for key in summary["exits"])
    early = HELPER.replace("found=i;break;","return i;")
    verify(candidates(analyze(early,HELPER_ROWS)),HELPER_ROWS)
    impure = "int shared=0;" + HELPER.replace("if(x<0)","shared++; if(x<0)")
    assert analyze(impure,HELPER_ROWS).program_analysis["phase95"]["status"]=="UNSUPPORTED_PROJECTION"
    assert not candidates(analyze(HELPER,HELPER_ROWS,phase95_components=frozenset({"windows"})))


@pytest.mark.parametrize("code,rows", [
    ("int f(int n){int i=0;while(i<n){i++;}return i;}",(((1,),1),((2,),3))),
    ("int f(int n){if(n<0){return 0;}return f(n-1);}",(((0,),1),((2,),3))),
    ("int f(int n){int a[n];a[0]=n;return a[0];}",(((1,),0),((2,),3))),
    ("int f(int n){int x=0;for(int i=0;i<n;i++){n--;x++;}return x;}",(((3,),1),((6,),3))),
])
def test_unsupported_effects_abstain(code,rows):
    result = analyze(code,rows)
    assert result.program_analysis["phase95"]["status"]=="UNSUPPORTED_PROJECTION"
    assert not candidates(result)


def test_reverse_guard_and_shadowed_variable_keep_range_and_window_behavior():
    reversed_guard = WINDOW.replace("i<n-2","n-2>i").replace("return peak;","{int peak=63;}return peak;")
    assert [row.actual for row in observations(WINDOW,WINDOW_ROWS).observations] == [
        row.actual for row in observations(reversed_guard,WINDOW_ROWS).observations]
    verify(candidates(analyze(reversed_guard,WINDOW_ROWS)),WINDOW_ROWS)


def test_profile_is_opt_in_and_worker_contract_stays_private():
    payload = {"code":GUARD,"mode":"examples","requirement":{"function":"f","examples":[
        {"args":args,"expected_return":out} for args,out in GUARD_ROWS]}}
    with client() as http:
        new = http.post("/v1/intention-analysis",json=payload | {"engine_version":95})
        assert new.status_code==200, new.text
        assert new.json()["candidates"][0]["hypothesis_origin"]=="phase95"
        earlier = http.post("/v1/intention-analysis",json=payload | {"engine_version":9}).json()
        assert "phase95" not in earlier["program_analysis"]
    assert 95 not in Batch.model_json_schema()["properties"]["engine_version"]["enum"]


@pytest.mark.skipif(not os.getenv("INTENTFORGE_VM_SOCKET"), reason="Requires the restricted Linux worker")
def test_worker_verifies_guard_with_unchanged_evidence_and_held_out_snapshot():
    payload = {"source":GUARD,"entry_point":"f","engine_version":95,"compare_candidates":True,
               "vectors":[{"arguments":args,"expected":out} for args,out in GUARD_ROWS]}
    with client() as http:
        reply = http.post(URL,json=payload)
        assert reply.status_code==200, reply.text
        evidence = reply.json()
        assert evidence["semantic_profile"]==95 and evidence["requires_approval"]
        assert evidence["program"]==program_identity(GUARD) and evidence["guided_evidence"]["confirmed_fault"]
        eligible = evidence["guided_evidence"]["recommended_candidate"]
        candidate = next(row for row in evidence["candidates"] if row["id"]==eligible)
        assert evidence["candidate_categories"][eligible]=="DOMAIN_BASE_CASE_CONSTRAINT"
        evaluated = http.post(URL,json=payload | {"source":candidate["source"],"compare_candidates":False,
            "vectors":[{"arguments":[-13],"expected":7},{"arguments":[9],"expected":46}]}).json()
        assert evaluated["guided_evidence"]["original"]=="ORIGINAL_MATCHES_SUPPLIED_TESTS"
        assert not evaluated["candidates"] and evaluated["specification"] is None
        assert http.post(URL,json=payload | {"language":"c"}).status_code==422
        assert http.post(URL,json=payload | {"runtime_observation":{}}).status_code==422
