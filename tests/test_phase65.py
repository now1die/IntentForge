"""Path feasibility, multi-argument recursion and review-only verification."""
import os

from fastapi.testclient import TestClient
import pytest

from ai.behavior_oracle import ExecutionLimits, Status, Vector
from ai.intention_context import Example
from ai.intention_engine import analyze_intention
from backend.app.main import app
from vm.behavioral_executor import MiniCOracle

MULTI = "int f(int n,int total){if(0>=n){return total;}return f(n,total+3);}"
SEQUENCE = "int f(int n){if(n<=1){return n+1;}return f(n-1)-f(n-2);}"
INTERMEDIATE = "int f(int n){int raw=n+3;int calibrated=raw*2;int report=calibrated+19;return raw;}"
URL = "/v1/behavioral-verification"


def analyze(source, examples=()):
    return analyze_intention(source, phase65=True, phase6_entry="f", phase6_examples=examples)


def evidence(result):
    return result.program_analysis["phase65"]


@pytest.mark.parametrize("guard", ["x>3", "3<x", "!(x<=3)", "x==4"])
def test_contradictory_atomic_comparisons_are_excluded(guard):
    result = analyze("int f(int x){if(x<=3){if("+guard+"){return 99;}return x;}return 7;}")
    excluded, inside, outside = evidence(result)["paths"]["f"]["returns"]
    assert excluded["feasibility"] == "excluded"
    assert inside["paths"][0]["facts"][0]["max"] == 3
    assert outside["paths"][0]["facts"][0]["min"] == 4


def test_inequality_shadowing_and_assignment_invalidation():
    source = "int f(int x){if(x!=4){if(x==4){return 99;}{int x=4;if(x==4){return x;}}x=4;if(x==4){return x;}}return 0;}"
    excluded, shadow, overwritten, fallback = evidence(analyze(source))["paths"]["f"]["returns"]
    assert excluded["feasibility"] == "excluded"
    assert shadow["feasibility"] == overwritten["feasibility"] == fallback["feasibility"] == "modeled"
    outer, = [fact for fact in shadow["paths"][0]["facts"] if fact["excluded"]]
    inner, = [fact for fact in shadow["paths"][0]["facts"] if not fact["excluded"]]
    assert outer["binding"] != inner["binding"] and outer["name"] == inner["name"] == "x"
    assert [fact["excluded"] for fact in overwritten["paths"][0]["facts"] if fact["binding"] == outer["binding"]] == [[]]


def test_disjunctive_definitions_and_explicit_path_limit():
    source = "int f(int n){int x=0;if(n<1){x=2;}else{x=3;}return x;}"
    row, = evidence(analyze(source))["paths"]["f"]["returns"]
    assert len(row["paths"]) == 2
    assert len({state["definitions"][0]["site"] for state in row["paths"]}) == 2
    big = "int f(bool a,bool b,bool c,bool d){int x=0;if(a){x++;}if(b){x++;}if(c){x++;}if(d){x++;}return x;}"
    limited = evidence(analyze(big))
    assert limited["status"] == "ANALYSIS_LIMITED" and not limited["paths"]["f"]["complete"]
    assert all(row["feasibility"] != "excluded" for row in limited["paths"]["f"]["returns"])


def test_loop_edges_and_possible_upstream_dependencies():
    source = "int f(int n){int raw=n+5;int total=raw*2;while(n>0){n--;if(n==2){break;}continue;}return total;}"
    details = evidence(analyze(source))["paths"]["f"]
    assert details["complete"]
    assert {edge["kind"] for edge in details["loop_edges"]} == {"true", "false", "back", "break", "continue"}
    assert all({item["name"] for item in path["possible_upstream_definitions"]} == {"raw", "n"}
               for path in details["returns"][0]["paths"])


def test_call_effects_and_reordered_return_dependencies():
    source = """int counter=0;
      int pick(int first,int second){counter++;return first;}
      int f(int p,int q){return pick(q,p);}
    """
    summary = evidence(analyze(source))["interprocedural"]
    assert summary["f"]["possible_global_writes"] == summary["pick"]["possible_global_writes"]
    assert len(summary["f"]["possible_global_writes"]) == 1
    assert summary["f"]["return_parameter_inputs"] == [1]
    call, = summary["f"]["call_sites"]
    assert call["feeds_return"] and call["callee_result_inputs"] == [0]
    assert [x["affine"]["name"] for x in call["arguments"]] == ["q", "p"]


def test_returned_global_may_depend_on_argument_through_a_call():
    source = "int g=0;int set(int n){g=n;return n;}int f(int x){set(x);return g;}"
    summary = evidence(analyze(source))["interprocedural"]["f"]
    assert summary["return_parameter_inputs"] == [0] and summary["possible_global_writes"]


def test_global_atomic_fact_dropped_at_call():
    source = "int g=0;int set(){g=4;return g;}int f(){if(g==0){set();if(g==4){return 2;}}return 3;}"
    row = evidence(analyze(source))["paths"]["f"]["returns"][0]
    assert row["feasibility"] == "modeled" and row["paths"][0]["facts"][0]["min"] == 4


def test_multi_argument_repair_keeps_accumulator_and_reports_affine_mapping():
    result = analyze(MULTI)
    candidate, = result.candidates
    assert candidate.compiler_valid and candidate.proposal.category == "RECURSIVE_PARAMETER_PROGRESS"
    assert "f(n - 1,total+3)" in candidate.proposed_code
    call, = evidence(result)["interprocedural"]["f"]["call_sites"]
    assert call["self_recursive"] and [a["affine"]["offset"] for a in call["arguments"]] == [0, 3]
    inputs = tuple(Vector(arguments=(n, s), expected=s+3*n) for n, s in [(0,7), (1,3), (4,-2)])
    assert MiniCOracle().verify(candidate.proposed_code, "f", inputs, ExecutionLimits()).status == Status.MATCHES_SUPPLIED_TESTS


@pytest.mark.parametrize("source", [
    "int f(int n,int total){if(n>=6){return total;}return f(n+1,total);}",
    "int f(int a,int b){if(a>=b){return b;}return f(a+1,b-1);}",
    "int other(int n,int a){if(n<=0){return a;}return f(n-1,a);}int f(int n,int a){return other(n,a);}",
    "int f(int n,int a){if(n<=0){return a;}return f(n-1,n-1);}",
])
def test_correct_and_mutual_recursion_abstain(source):
    assert not any(c.proposal.category == "RECURSIVE_PARAMETER_PROGRESS" for c in analyze(source).candidates)


@pytest.mark.parametrize("examples", [(), (Example((0,),1),), (Example((True,),1),), (Example((3,4),1),)])
def test_recurrence_has_structure_without_a_valid_guiding_input(examples):
    result = analyze(SEQUENCE, examples)
    assert not result.candidates
    row, = evidence(result)["paths"]["f"]["recursive_returns"]
    assert row["self_calls"] == 2 and row["root_operator"] == "-"


def test_recurrence_guide_yields_two_valid_token_edits_and_no_claimed_runtime():
    result = analyze(SEQUENCE, (Example((4,),8),))
    choices = result.to_dict()["candidates"]
    assert {row["edits"][0]["proposed"] for row in choices} == {"+", "*"}
    assert all(row["compiler_valid"] and row["requires_approval"] and row["behavioral_status"] == "ORACLE_UNAVAILABLE"
               and row["evidence_basis"] == "supplied_examples" and row["hypothesis_origin"] == "phase65" for row in choices)


def test_legitimate_intermediate_and_path_specific_candidate_have_counter_evidence():
    assert analyze_intention(INTERMEDIATE, phase6=True).candidates
    result = analyze(INTERMEDIATE)
    assert not result.candidates and evidence(result)["withheld"][0]["category"] == "RETURN_DEPENDENCY_MISMATCH"
    source = INTERMEDIATE.replace("int n)", "int n,int m)").replace("return raw;", "if(m<0){return raw;}return report;")
    assert not analyze(source).candidates
    result = analyze(source, (Example((6,-1),37), Example((6,1),37)))
    choice, = result.to_dict()["candidates"]
    assert choice["category"] == "PATH_RETURN_DEPENDENCY" and choice["counter_evidence"]


def test_phase65_gateway_is_opt_in_and_rejects_fabricated_evidence(monkeypatch):
    request = dict(source=MULTI, entry_point="f", engine_version=65, compare_candidates=True,
                   vectors=[{"arguments":[4,2], "expected":14}])
    with TestClient(app, base_url="http://127.0.0.1:8000", client=("127.0.0.1", 41020)) as client:
        assert client.post(URL, json=request | {"actual":14}).status_code == 422
        legacy = client.post("/v1/intention-analysis", json={"code": MULTI, "engine_version":6, "mode":"code_only"}).json()
        assert "phase65" not in legacy["program_analysis"]
        latest = client.post("/v1/intention-analysis", json={"code": MULTI, "engine_version":65, "mode":"code_only"}).json()
        assert latest["candidates"][0]["hypothesis_origin"] == "phase65"
        if os.getenv("INTENTFORGE_VM_SOCKET"):
            answer = client.post(URL, json=request).json()
            assert answer["availability"]["status"] == "available"
            assert answer["original"]["execution"]["issue"]["code"] == "CALL_DEPTH"
            assert answer["comparison_status"] == "ONE_MATCH" and answer["requires_approval"]
            ambiguous = request | {"source": "int f(int n){if(n<=1){return n;}return f(n-1)*f(n-2);}",
                                   "vectors": [{"arguments":[2], "expected":1}]}
            reply = client.post(URL, json=ambiguous).json()
            assert reply["comparison_status"] == "MULTIPLE_MATCHES" and reply["requires_approval"]
        monkeypatch.delenv("INTENTFORGE_VM_GATEWAY", raising=False)
        assert client.post(URL, json=request).json()["availability"]["status"] == "disabled"
