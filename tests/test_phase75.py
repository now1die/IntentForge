"""Semantic repair hypotheses and the unchanged Phase 7 evidence boundary."""
import os

import pytest
from fastapi.testclient import TestClient

from ai.behavior_oracle import ExecutionLimits, Status, Vector, program_identity
from ai.intention_context import Example
from ai.intention_engine import analyze_intention
from backend.app.main import app
from vm.behavioral_executor import MiniCOracle

STEP = "int f(int n,int total){if(n<=0){return total;}return f(n-1,total+n);}"
STEP_VECTORS = ((4,0),(7,0),(8,2))
WEIGHTED = "int f(int n){if(n<=1){return n;}int prior=f(n-1);int twice=2*f(n-2);return prior-twice;}"
HELPER = "int add(int a){int prior=a+4;return prior;}int f(int index,int a){if(index<=0){return a;}return add(f(index,a));}"
URL = "/v1/behavioral-verification"


def analysis(source, suite=(), **settings):
    return analyze_intention(source, phase75=True, phase6_entry="f",
                             phase6_examples=tuple(Example(args, expected) for args, expected in suite), **settings)


def verified(source, suite):
    vectors = tuple(Vector(arguments=args, expected=value) for args,value in suite)
    return MiniCOracle().verify(source,"f",vectors,ExecutionLimits())


def step_suite():
    return tuple((args,args[1]+sum(range(args[0],0,-2))) for args in STEP_VECTORS)


def test_nonunit_progress_requires_diverse_typed_recursive_inputs():
    for vectors in ((), step_suite()[:1], (((False,0),0),((True,0),0)), (((0,0),0),((-1,0),0))):
        assert "NONUNIT_RECURSIVE_PROGRESS" not in {c.proposal.category for c in analysis(STEP,vectors).candidates}
    result = analysis(STEP,step_suite())
    choices = [c for c in result.candidates if c.proposal.category=="NONUNIT_RECURSIVE_PROGRESS"]
    assert len(choices)==3
    correct, = [c for c in choices if verified(c.proposed_code,step_suite()).status==Status.MATCHES_SUPPLIED_TESTS]
    assert "f(n - 2,total+n)" in correct.proposed_code
    report = result.to_dict()
    row = next(c for c in report["candidates"] if c["id"]==correct.id)
    assert row["compiler_valid"] and row["requires_approval"] and row["source_snapshot"]==program_identity(STEP)
    assert row["evidence_basis"]=="supplied_examples" and row["counter_evidence"]


@pytest.mark.parametrize("operator", ["+", "-"])
def test_variable_step_summary_and_guided_variable_hypothesis(operator):
    if operator=="-":
        source="int f(int x,int step,int score){if(x<=0){return score;}return f(x-1,step,score+x);}"
        suite=tuple((args,args[2]+sum(range(args[0],0,-args[1]))) for args in [(7,2,0),(9,3,4),(6,4,1)])
    else:
        source="int f(int x,int step,int score){if(x>=10){return score;}return f(x+2,step,score+x);}"
        suite=tuple((args,args[2]+sum(range(args[0],10,args[1]))) for args in [(1,2,0),(4,3,4),(0,4,1)])
    result=analysis(source,suite)
    candidate=next(c for c in result.candidates if f"x {operator} step" in c.proposed_code)
    assert verified(candidate.proposed_code,suite).status==Status.MATCHES_SUPPLIED_TESTS
    summary=analysis(candidate.proposed_code).program_analysis["phase65"]["progress"]["f"]
    assert summary["complete"] and summary["calls"][0]["argument"]["step_name"]=="step"
    assert summary["calls"][0]["feeds_return"]


def test_weighted_local_recurrence_edits_only_combining_operator():
    suite=tuple(((n,), (2**n-(-1)**n)//3) for n in (3,4,6))
    assert not analysis(WEIGHTED).candidates
    result=analysis(WEIGHTED,suite)
    exact=next(c for c in result.candidates if "return prior+twice;" in c.proposed_code)
    edit,=exact.proposal.edits
    assert WEIGHTED[edit.span.start.offset:edit.span.end.offset]=="-" and exact.compiler_valid
    assert verified(exact.proposed_code,suite).status==Status.MATCHES_SUPPLIED_TESTS


@pytest.mark.parametrize("declaration", ["", "{int a=91;}", "{int a=84;{int a=4;}}"])
def test_local_helper_shadow_scope_preserves_repair_span_and_behavior(declaration):
    source=HELPER.replace("{int prior","{"+declaration+"int prior")
    suite=(((2,4),12),((5,-3),17))
    result=analysis(source)
    choice,=result.candidates
    edit,=choice.proposal.edits
    assert source[edit.span.start.offset:edit.span.end.offset]=="index"
    assert choice.compiler_valid
    assert result.program_analysis["phase65"]["interprocedural"]["add"]["scalar_helper"]["modeled_returns"]==1
    assert verified(source,suite).status==Status.EXECUTION_LIMITED
    assert verified(choice.proposed_code,suite).status==Status.MATCHES_SUPPLIED_TESTS


def test_branch_helper_argument_requires_an_independently_varying_unused_parameter():
    source="int h(int x,int y){if(x>5){return y+5;}return x+y;}int f(int a,int b,int c,int d){return h(a,c)+h(a,d);}"
    sparse=(((1,3,4,7),15),((2,4,3,5),14))
    assert not analysis(source,sparse).candidates
    suite=(((1,3,4,7),15),((1,4,4,7),16),((7,2,-1,3),9))
    result=analysis(source,suite)
    assert result.program_analysis["phase65"]["interprocedural"]["h"]["scalar_helper"]["modeled_returns"]==2
    assert len(result.candidates)==2
    assert sum(verified(c.proposed_code,suite).status==Status.MATCHES_SUPPLIED_TESTS for c in result.candidates)==2


def test_radix_repair_uses_a_lexically_related_remainder():
    source="int f(int v){int result=0;while(v>0){result+=v%7;v/=6;}return result;}"
    suite=(((23,),5),((50,),2))
    assert not analysis(source).candidates
    choice,=analysis(source,suite).candidates
    assert choice.proposal.category=="RADIX_PROGRESS_MISMATCH" and "v/=7" in choice.proposed_code
    assert verified(choice.proposed_code,suite).status==Status.MATCHES_SUPPLIED_TESTS
    shadow=source.replace("result+=v%7;","{int v=21;result+=v%7;}")
    assert not analysis(shadow,suite).candidates


@pytest.mark.parametrize("source", [
    "int g=1;int h(int x){g++;return x;}int f(int n,int s){if(n<=0){return s;}return h(f(n,s));}",
    "int f(int lo,int hi,int sum){if(lo>=hi){return sum;}return f(lo+2,hi,sum+lo);}",
    "int f(int n,int sum){if(n<=0){return sum;}return f(n-2,sum+n);}",
    "int f(int n,int sum){if(n++<=0){return sum;}return f(n,sum+n);}",
])
def test_unsupported_or_correct_recursion_does_not_gain_code_only_edits(source):
    result=analysis(source)
    assert not result.candidates
    assert "f" in result.program_analysis["phase65"]["progress"]


def test_static_api_preserves_previous_contract_and_rejects_conflicting_examples(monkeypatch):
    monkeypatch.delenv("INTENTFORGE_VM_GATEWAY",raising=False)
    client=TestClient(app)
    body=dict(code=STEP,mode="examples",requirement={"function":"f","examples":[
        {"args":list(args),"expected_return":expected} for args,expected in step_suite()]})
    old=client.post("/v1/intention-analysis",json=body|{"engine_version":7}).json()
    new=client.post("/v1/intention-analysis",json=body|{"engine_version":75}).json()
    assert "progress" not in old["program_analysis"]["phase65"]
    assert new["guided_evidence"]=="POSSIBLE_REPAIR" and new["behavioral_status"]=="ORACLE_UNAVAILABLE"
    assert new["program_analysis"]["phase65"]["progress"]["f"]["calls"][0]["argument"]=={"offset":-1}
    request=dict(source=STEP, entry_point="f", engine_version=75, compare_candidates=True,
                 vectors=[{"arguments":[4,0],"expected":6}])
    assert client.post(URL,json=request|{"actual":6}).status_code==422
    assert client.post(URL,json=request|{"language":"c"}).status_code==422
    assert client.post(URL,json=request|{"vectors":[{"arguments":[4,0],"expected":6},{"arguments":[4,0],"expected":10}]}).status_code==422
    assert client.post(URL,json=request).json()["guided_evidence"]["original"]=="VERIFICATION_UNAVAILABLE"


@pytest.mark.skipif(not os.getenv("INTENTFORGE_VM_SOCKET"), reason="Requires the restricted worker")
def test_isolated_nonunit_approval_status_and_resource_stop():
    with TestClient(app,base_url="http://127.0.0.1:8000",client=("127.0.0.1",41753)) as client:
        request=dict(source=STEP,entry_point="f",engine_version=75,compare_candidates=True,
                     vectors=[{"arguments":list(args),"expected":expected} for args,expected in step_suite()])
        fault=client.post(URL,json=request).json()
        assert fault["guided_evidence"]["original"]=="CONFIRMED_TEST_MISMATCH" and fault["requires_approval"]
        passing=next(c for c in fault["candidates"] if c["id"]==fault["guided_evidence"]["recommended_candidate"])
        assert "f(n - 2,total+n)" in passing["source"]
        match=client.post(URL,json=request|{"source":passing["source"]}).json()
        assert match["guided_evidence"]["original"]=="ORIGINAL_MATCHES_SUPPLIED_TESTS"
        assert not match["guided_evidence"]["confirmed_fault"] and match["guided_evidence"]["recommended_candidate"] is None
        limited=client.post(URL,json=request|{"source":STEP.replace("f(n-1","f(n")}).json()
        assert limited["guided_evidence"]["original"]=="EXECUTION_LIMITED"
        assert not limited["guided_evidence"]["confirmed_fault"]
