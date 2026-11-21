"""Phase 8 typed constraints, arithmetic witnesses and verified presentation."""
import os

import pytest
from fastapi.testclient import TestClient

from ai.behavior_oracle import ExecutionLimits, Status, Vector, program_identity
from ai.intention_context import Example
from ai.intention_engine import analyze_intention
from ai.intention_phase8 import CATEGORIES, MAX_PROPOSALS, arithmetic_value
from ai.specification import Bounds, InvalidSpecification
from backend.app.main import app
from vm.behavioral_executor import MiniCOracle

URL = "/v1/behavioral-verification"
PREDECESSOR = "int f(int a,int n,int d){return a+n*d;}"
PREDECESSOR_CASES = (((3,2,4),7),((2,4,5),17),((7,1,6),7))
CORRECT_NONUNIT = "int f(int n,int a){if(n<=0){return a;}return f(n-2,a+n);}"


def analyze(source, rows=(), **settings):
    return analyze_intention(source, phase8=True, phase6_entry="f",
                             phase6_examples=tuple(Example(args,expected) for args,expected in rows), **settings)


def observations(source, rows):
    return MiniCOracle().verify(source,"f",tuple(Vector(arguments=args,expected=expected) for args,expected in rows),ExecutionLimits())


def client():
    return TestClient(app,base_url="http://127.0.0.1:8000",client=("127.0.0.1",41942))


def test_specification_separates_partial_inputs_from_expected_outputs():
    bounds = (Bounds(minimum=0,maximum=9),)
    source = "int f(int a){return 2*a+1;}"
    analysis = analyze(source,phase8_domain=bounds,phase8_partial=((2,),))
    spec = analysis.program_analysis["phase8"]["specification"]
    assert spec["status"] == "INCOMPLETE_SPECIFICATION" and spec["trusted_examples"]==0
    assert spec["partial_inputs"]==1 and spec["source_snapshot"]==program_identity(source)
    assert not analysis.candidates


@pytest.mark.parametrize(("source","examples","bounds"), [
    ("int f(int x){return x;}",(((True,),1),),None),
    ("int f(int x){return x;}",(((1,),True),),None),
    ("int f(int x){return x;}",(((3,),3),),(Bounds(minimum=-2,maximum=2),)),
    ("bool f(bool x){return x;}",(((True,),True),),(Bounds(minimum=0,maximum=1),)),
    ("int f(int x){return x;}",(((1,),1),((1,),2)),None),
    ("int f(int x){return x;}",(((2**31,),1),),None),
    ("int g(int x){return x;}",(((1,),1),),None),
])
def test_invalid_signature_or_domain_constraints_are_rejected(source,examples,bounds):
    with pytest.raises(InvalidSpecification):
        analyze(source,examples,phase8_domain=bounds)


def test_closed_form_and_predecessor_require_examples_and_compiler_validation():
    assert not analyze(PREDECESSOR).candidates
    result = analyze(PREDECESSOR,PREDECESSOR_CASES)
    candidate, = result.candidates
    assert candidate.proposal.category=="ARITHMETIC_PREDECESSOR" and candidate.compiler_valid
    assert "a+(n - 1)*d" in candidate.proposed_code
    assert observations(candidate.proposed_code,PREDECESSOR_CASES).status==Status.MATCHES_SUPPLIED_TESTS
    alternative = "int f(int n,int side){return n+(side-3)*n*(n-1)/2;}"
    rows = tuple(((n,s),n+(s-4)*sum(range(n))) for n,s in [(1,7),(3,8),(6,4),(5,9)])
    analysis = analyze(alternative,rows)
    exact = next(c for c in analysis.candidates if "side-4" in c.proposed_code)
    assert exact.compiler_valid and observations(exact.proposed_code,rows).status==Status.MATCHES_SUPPLIED_TESTS
    assert analysis.program_analysis["phase8"]["constraints"]["minimum_changed_tokens"]==1


def test_original_arithmetic_agreement_retains_empty_phase8_pool():
    source = "int f(int a,int n,int d){return a+n*d;}"
    rows = tuple((args,args[0]+args[1]*args[2]) for args,_ in PREDECESSOR_CASES)
    analysis = analyze(source,rows)
    assert not analysis.candidates
    assert analysis.program_analysis["phase8"]["constraints"]["status"]=="CONSTRAINTS_ALREADY_AGREE"


def test_helper_local_returns_preserve_the_sharing_and_lexical_binding():
    source = "int h(int x){{int x=9;}int raw=x+2;int final=raw*3;return raw;}int f(int n,int base){return base+h(n)+h(n+1);}"
    rows = tuple(((n,a),a+3*(2*n+5)) for n,a in [(0,6),(3,2),(-4,9)])
    result = analyze(source,rows)
    choice = next(c for c in result.candidates if c.proposal.category=="ARITHMETIC_RETURN_DEPENDENCY")
    assert "return final;" in choice.proposed_code and "base+h(n)+h(n+1)" in choice.proposed_code
    assert observations(choice.proposed_code,rows).status==Status.MATCHES_SUPPLIED_TESTS
    assert result.program_analysis["phase8"]["constraints"]["helper_functions"]==["h"]
    assert result.to_dict()["candidates"][0]["requires_approval"]
    prohibited = "int counter=0;int h(int x){counter++;return x+2;}int f(int x){return h(x)*3;}"
    assert not any(c.proposal.category in CATEGORIES for c in analyze(prohibited,(((1,),4),((5,),10))).candidates)


def test_arithmetic_grammar_preserves_checked_faults_and_signed_remainder():
    assert arithmetic_value("/",-9,4)==-2 and arithmetic_value("%",-9,4)==-1
    for operation,a,b in [("/",1,0),("%",-(2**31),-1),("+",2**31-1,1)]:
        with pytest.raises(ArithmeticError):
            arithmetic_value(operation,a,b)
    result = analyze("int f(int n){return (n+2)*9;}",(((2**31-1,),2),((2,),1)))
    assert result.program_analysis["phase8"]["constraints"]["status"]=="UNSUPPORTED_CHECKED_ARITHMETIC"
    assert not any(c.proposal.category in CATEGORIES for c in result.candidates)


def test_discovery_equivalent_alternatives_are_bounded_and_can_fail_holdout():
    source="int f(int x,int y){return (x+1)*(y+3);}"
    examples=tuple(((x,x-2),(x+1)*x) for x in (4,6,8))
    result=analyze(source,examples)
    candidates=[c for c in result.candidates if c.proposal.category in CATEGORIES]
    assert 2 <= len(candidates) <= MAX_PROPOSALS
    holdout=(((3,7),36),((-1,5),0))
    statuses=[observations(c.proposed_code,holdout).status for c in candidates]
    assert Status.MATCHES_SUPPLIED_TESTS in statuses and Status.MISMATCHES_SUPPLIED_TESTS in statuses


def test_public_static_contract_and_legacy_profiles():
    body=dict(code=PREDECESSOR,mode="examples",requirement={"function":"f","examples":[
        {"args":list(args),"expected_return":expected} for args,expected in PREDECESSOR_CASES]})
    with client() as http:
        prior=http.post("/v1/intention-analysis",json=body|{"engine_version":75}).json()
        assert "phase8" not in prior["program_analysis"]
        assert http.post("/v1/intention-analysis",json=body|{"engine_version":75,"partial_inputs":[]}).status_code==422
        current=http.post("/v1/intention-analysis",json=body|{"engine_version":8,
            "input_domain":[None,{"minimum":1,"maximum":5},None],"partial_inputs":[[1,2,3]]}).json()
        assert current["guided_evidence"]=="POSSIBLE_REPAIR"
        assert current["behavioral_status"]=="ORACLE_UNAVAILABLE"
        assert current["program_analysis"]["phase8"]["specification"]["partial_inputs"]==1
        assert current["candidates"][0]["hypothesis_origin"]=="phase8"
        bad=http.post("/v1/intention-analysis",json=body|{"engine_version":8,"input_domain":[None]})
        assert bad.status_code==422
        partial=http.post("/v1/intention-analysis",json={"code":PREDECESSOR,"mode":"examples","engine_version":8,
                    "requirement":{"function":"f"},"partial_inputs":[[3,2,4]]}).json()
        assert partial["program_analysis"]["phase8"]["specification"]["trusted_examples"]==0


def test_new_domain_whitelist_rejects_observations_disguised_as_requirements(monkeypatch):
    monkeypatch.delenv("INTENTFORGE_VM_GATEWAY",raising=False)
    with client() as http:
        body=dict(source=PREDECESSOR,engine_version=8,entry_point="f",compare_candidates=True,
                  vectors=[{"arguments":[3,2,4],"expected":7}])
        assert http.post(URL,json=body|{"actual":7}).status_code==422
        assert http.post(URL,json=body|{"language":"c"}).status_code==422
        assert http.post(URL,json=body|{"input_domain":[None,{"minimum":3,"maximum":5},None]}).status_code==422
        assert http.post(URL,json=body|{"engine_version":75,"input_domain":[None,None,None]}).status_code==422
        assert http.post(URL,json=body|{"engine_version":75,"input_domain":None}).status_code==422
        assert http.post(URL,json=body).json()["guided_evidence"]["original"]=="VERIFICATION_UNAVAILABLE"


@pytest.mark.skipif(not os.getenv("INTENTFORGE_VM_SOCKET"), reason="Requires the restricted Linux worker")
def test_isolated_verified_fault_approval_and_same_pool_review_policy():
    with client() as http:
        body=dict(source=PREDECESSOR,engine_version=8,entry_point="f",compare_candidates=True,
                  vectors=[{"arguments":list(args),"expected":out} for args,out in PREDECESSOR_CASES])
        verdict=http.post(URL,json=body).json()
        assert verdict["guided_evidence"]["confirmed_fault"] and verdict["requires_approval"]
        assert verdict["guided_evidence"]["recommended_candidate"] in verdict["candidate_details"]
        good=dict(source=CORRECT_NONUNIT,entry_point="f",compare_candidates=True,
                  vectors=[{"arguments":[4,0],"expected":6},{"arguments":[7,0],"expected":16}])
        prior=http.post(URL,json=good|{"engine_version":75}).json()
        updated=http.post(URL,json=good|{"engine_version":8}).json()
        assert updated["guided_evidence"]["original"]=="ORIGINAL_MATCHES_SUPPLIED_TESTS"
        assert updated["review_presentation"]=="OPTIONAL_COLLAPSED" and updated["candidates"]
        assert [row["id"] for row in updated["candidates"]]==[row["id"] for row in prior["candidates"]]
        domain=[{"minimum":0,"maximum":7},{"minimum":0,"maximum":1}]
        scoped=http.post(URL,json=good|{"engine_version":8,"input_domain":domain}).json()
        assert scoped["availability"]["status"]=="available"
        assert all(0 <= args[0] <= 7 and 0 <= args[1] <= 1
                   for probe in scoped["probes"] for args in [probe["arguments"]])
        assert all("expected" not in probe for probe in scoped["probes"])
