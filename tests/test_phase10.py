"""Checked Phase 10 projection, exact edits and separated worker evidence."""
import os

import pytest

from ai.behavior_oracle import Status, program_identity
from ai.intention_context import Example
from ai.intention_engine import analyze_intention
from ai.intention_phase10 import CATEGORIES
from benchmarks.phase95_fixtures import fixtures
from execution_service.contracts import Batch
from tests.test_phase8 import URL, client, observations

RECURSION = """int lookup(int key,int p,int q,int a,int b,int c) {
int cells[3];cells[0]=a;cells[1]=b;cells[2]=c;
if(p>q){return -1;}int middle=p+(q-p)/2;int current=cells[middle];
if(current==key){return middle;}
if(key<current){return lookup(key,p,middle-1,a,b,c);}
return lookup(key,middle+1,q,a,b,c);}
int f(int key,int a,int b,int c){return lookup(key,0,3,a,b,c);}"""
ROWS = (((12,2,5,8),-1),((8,2,5,8),2),((2,2,5,8),0),((4,2,5,8),-1),((5,2,5,8),1))


def analyze(code,rows,**settings):
    return analyze_intention(code,phase10=True,phase6_entry="f",
                             phase6_examples=tuple(Example(args,expected) for args,expected in rows),**settings)


def new(result):
    return [choice for choice in result.candidates if choice.proposal.category in CATEGORIES]


def matches(result,rows,category):
    selected=next(choice for choice in new(result) if choice.proposal.category==category)
    assert selected.compiler_valid
    assert observations(selected.proposed_code,rows).status==Status.MATCHES_SUPPLIED_TESTS
    return selected


def test_recursive_extent_evidence_excludes_runtime_failure_from_confirmed_output():
    result=analyze(RECURSION,ROWS)
    choice=matches(result,ROWS+(((17,1,6,14),-1),),"SEARCH_INTERVAL_CONSTRAINT")
    assert "lookup(key,0,2" in choice.proposed_code
    projection=result.program_analysis["phase10"]
    assert projection["arrays"][0]["length"]==3
    assert projection["search_intervals"][0]["inclusive"]
    assert any(not cell["valid"] and cell["maximum"]==3 for cell in projection["accesses"])
    recorded=next(row for row in result.to_dict()["candidates"] if row["id"]==choice.id)
    assert recorded["source_snapshot"]==program_identity(RECURSION) and recorded["requires_approval"]
    assert not new(analyze(choice.proposed_code,ROWS))


def test_interval_base_case_requires_two_failed_misses_and_known_hits():
    source=RECURSION.replace("if(p>q){return -1;}","").replace("lookup(key,0,3","lookup(key,0,2")
    match=matches(analyze(source,ROWS),ROWS,"SEARCH_INTERVAL_CONSTRAINT")
    assert "if (q < p)" in match.proposed_code and len(match.proposal.edits)==1
    assert not new(analyze(source,ROWS[1:4]))


def test_half_open_and_singleton_controls_and_unknown_progress():
    control=RECURSION.replace("if(p>q)","if(p>=q)").replace("middle-1","middle")
    assert not new(analyze(control,ROWS))
    stopper=RECURSION.replace("middle+1,q","p,q")
    report=analyze(stopper,ROWS).program_analysis["phase10"]
    assert "SEARCH_INTERVAL_DID_NOT_SHRINK" in report["sample_issues"]
    assert not new(analyze(stopper,ROWS))
    singleton="int f(int key,int v){int a[1];a[0]=v;if(key==a[0]){return 0;}return -1;}"
    assert not new(analyze(singleton,(((2,2),0),((9,2),-1))))


def test_expanding_handoff_and_negative_sentinel_are_atomic():
    case=next(row for row in fixtures() if row["id"]=="expanding-search-boundary-fault")
    rows=tuple((tuple(v["arguments"]),v["expected"]) for v in case["vectors"]+case["holdout_vectors"])
    result=analyze(case["source"],rows[:len(case["vectors"])])
    choice=matches(result,rows,"EXPANDING_HANDOFF_CONSTRAINT")
    assert len(choice.proposal.edits)==2 and choice.proposed_code==case["references"][0]
    assert {row["kind"] for row in result.program_analysis["phase10"]["progress"]}=={"growth","interval"}


def test_fixed_index_and_shifted_origin_require_checked_cells():
    fixed="int f(int p,int a,int b){int box[2];box[0]=a;box[1]=b;return box[p+1];}"
    fixed_rows=(((0,3,8),3),((1,6,5),5),((0,-1,0),-1))
    matches(analyze(fixed,fixed_rows),fixed_rows,"FIXED_ARRAY_INDEX_CONSTRAINT")
    shifted="""int f(int origin,int d,int e,int g){int box[3];box[0]=d;box[1]=e;box[2]=g;
    int sum=0;for(int p=origin;p<origin+3;p++){sum+=box[p-0];}return sum;}"""
    rows=(((0,5,7,-2),10),((2,4,1,9),14),((-2,7,0,4),11))
    choice=matches(analyze(shifted,rows),rows,"DERIVED_RANGE_CONSTRAINT")
    assert "box[p-origin]" in choice.proposed_code
    assert not new(analyze(fixed,(((2,3,8),0),((3,6,5),0))))


def test_modulo_helper_repeated_calls_and_short_circuit():
    source="""int reduce(int a,int b){while(b!=0){int rest=a%b;a=b;b=rest;}return a;}
    int f(int n){int count=0;for(int k=1;k<=n;k++){if(reduce(n,k)!=2){count++;}}return count;}"""
    from math import gcd
    rows=tuple(((n,),sum(gcd(n,k)==2 for k in range(1,n+1))) for n in (2,6,12,9,20))
    result=analyze(source,rows)
    matches(result,rows,"HELPER_PROGRESS_CONSTRAINT")
    assert any(row["kind"]=="remainder" for row in result.program_analysis["phase10"]["progress"])
    assert analyze(source.replace("b=rest","b=rest+b"),rows).program_analysis["phase10"]["status"]=="UNSUPPORTED_PROJECTION"


def test_source_metamorphisms_and_private_wire_version():
    changed=RECURSION.replace("if(p>q)","if(q<p)").replace("int current","{int other=7;}int current")
    matches(analyze(changed,ROWS),ROWS,"SEARCH_INTERVAL_CONSTRAINT")
    assert 10 not in Batch.model_json_schema()["properties"]["engine_version"]["enum"]


@pytest.mark.skipif(not os.getenv("INTENTFORGE_VM_SOCKET"), reason="Requires the restricted Linux worker")
def test_isolated_runtime_classification_and_fresh_holdout():
    payload={"source":RECURSION,"entry_point":"f","engine_version":10,"compare_candidates":True,
             "vectors":[{"arguments":args,"expected":expected} for args,expected in ROWS]}
    with client() as http:
        reply=http.post(URL,json=payload)
        assert reply.status_code==200,reply.text
        data=reply.json()
        assert data["semantic_profile"]==10 and data["requires_approval"]
        assert data["guided_evidence"]["original"]=="RUNTIME_FAILURE"
        assert not data["guided_evidence"]["confirmed_fault"]
        assert data["guided_evidence"]["recommended_candidate"] is None
        candidate=next(c for c in data["candidates"] if data["candidate_categories"][c["id"]]=="SEARCH_INTERVAL_CONSTRAINT")
        assert data["runtime_observation"]["alternatives"][candidate["id"]]["matched_trusted_suite"]
        held=http.post(URL,json=payload | {"source":candidate["source"],"compare_candidates":False,
             "vectors":[{"arguments":[-7,1,6,14],"expected":-1}]}).json()
        assert not held["candidates"] and held["guided_evidence"]["original"]=="ORIGINAL_MATCHES_SUPPLIED_TESTS"
        assert http.post(URL,json=payload | {"runtime_observation":{}}).status_code==422
        assert http.post(URL,json=payload | {"language":"c"}).status_code==422
