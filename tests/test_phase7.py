"""Phase 7 evidence, semantic normalization and the isolated gateway."""
import os

import pytest
from fastapi.testclient import TestClient

from ai.behavior_oracle import ExecutionLimits, Status, Vector
from ai.guided_evidence import OriginalEvidence, ReviewEvidence, classify_original, classify_review
from ai.intention_context import Example
from ai.intention_engine import analyze_intention
from backend.app.main import app
from execution_service.probes import guided_inputs
from vm.behavioral_executor import MiniCOracle
from vm.interpreter import prepare

URL = "/v1/behavioral-verification"
SUBTRACTION = "int f(int n){if(n<=1){return n;}return f(n-1)-f(n-2);}"
ADDITION = SUBTRACTION.replace("f(n-1)-f(n-2)", "f(n-1)+f(n-2)")
MULTIPLICATION = SUBTRACTION.replace("f(n-1)-f(n-2)", "f(n-1)*f(n-2)")
BASE = "int f(int n,int total){if(n<=0){return total;}return f(n,total+3);}"


def isolated_client():
    return TestClient(app, base_url="http://127.0.0.1:8000", client=("127.0.0.1", 41307))


def verify_payload(source, expected=3, n=4, version=7):
    return dict(source=source, vectors=[{"arguments": [n], "expected": expected}],
                engine_version=version, entry_point="f", compare_candidates=True)


@pytest.mark.parametrize(("source", "expected", "evidence"), [
    ("int f(int n){return n+1;}", 5, OriginalEvidence.ORIGINAL_MATCHES_SUPPLIED_TESTS),
    ("int f(int n){return n+2;}", 5, OriginalEvidence.CONFIRMED_TEST_MISMATCH),
    ("int f(int n){return f(n);}", 5, OriginalEvidence.EXECUTION_LIMITED),
    ("int f(int n){return 1/(n-4);}", 5, OriginalEvidence.RUNTIME_FAILURE),
    ("int f(int n){return undeclared;}", 5, OriginalEvidence.EXECUTION_UNSUPPORTED),
])
def test_original_status_separates_agreement_mismatch_and_execution(source, expected, evidence):
    original = MiniCOracle().verify(source, "f", (Vector(arguments=(4,), expected=expected),), ExecutionLimits())
    assert classify_original(original) == evidence
    review = classify_review(evidence, 1, 1)
    if evidence == OriginalEvidence.CONFIRMED_TEST_MISMATCH:
        assert review == ReviewEvidence.REVIEW_MATCHING_REPAIR
    else:
        assert review == ReviewEvidence.POSSIBLE_REPAIR


@pytest.mark.parametrize("layout", [
    "int f(int n,int total){if(!(n<=0)){return f(n,total+3);}return total;}",
    "int f(int n,int total){if(0<n){return f(n,total+3);}else{return total;}}",
    "int f(int n,int total){if(n<=0){{int n=22;}return total;}return f(n,total+3);}",
    "int f(int n,int total){{int n=77;}{{if(n<=0){return total;}}return f(n,total+3);}}",
])
def test_cfg_variations_repair_the_same_lexical_argument(layout):
    vectors = tuple(Vector(arguments=(n,t), expected=t+3*n) for n,t in [(0,4),(1,-3),(3,2)])
    assert not analyze_intention(layout,phase65=True).candidates
    original = MiniCOracle().verify(layout,"f",vectors,ExecutionLimits())
    assert original.status == Status.EXECUTION_LIMITED
    result = analyze_intention(layout,phase7=True)
    choice, = result.candidates
    edit, = choice.proposal.edits
    assert choice.compiler_valid and choice.proposal.category == "RECURSIVE_PARAMETER_PROGRESS"
    assert layout[edit.span.start.offset:edit.span.end.offset] == "n"
    assert MiniCOracle().verify(choice.proposed_code,"f",vectors,ExecutionLimits()).status == Status.MATCHES_SUPPLIED_TESTS


@pytest.mark.parametrize("source", [
    BASE.replace("if(n<=0)", "if(n++<=0)"),
    BASE.replace("return f(n,total+3);", "n--;return f(n,total+3);"),
    BASE.replace("return f(n,total+3);", "{int n=1;return f(n,total+3);}"),
    "int g=0;int increment(int v){g++;return v+2;}"+BASE.replace("return f(n,total+3);","return increment(f(n,total+3));"),
])
def test_effectful_or_relevant_shadow_layout_remains_outside_rule(source):
    assert not any(c.proposal.category == "RECURSIVE_PARAMETER_PROGRESS" for c in analyze_intention(source,phase7=True).candidates)


def test_scalar_helpers_are_bounded_and_support_nested_progress():
    source = "int inc(int x){return x+3;}int helper(int x){return inc(x);}"+BASE.replace(
        "return f(n,total+3);","return helper(f(n,total));")
    result = analyze_intention(source,phase7=True)
    assert not analyze_intention(source, phase7=True, phase7_components=frozenset({"layout"})).candidates
    assert result.program_analysis["phase65"]["interprocedural"]["helper"]["scalar_helper"] == {
        "parameter_inputs":[0], "depth":1, "identity_parameter":None}
    choice, = result.candidates
    suite = tuple(Vector(arguments=(n, total), expected=total+3*n) for n,total in [(1,7),(4,-3)])
    assert MiniCOracle().verify(choice.proposed_code,"f",suite,ExecutionLimits()).status == Status.MATCHES_SUPPLIED_TESTS


def test_identity_helper_recurrence_edits_inner_operator_only():
    source = "int pass(int row){return row;}"+SUBTRACTION.replace("return f(n-1)-f(n-2);","return pass(f(n-1)-f(n-2));")
    result = analyze_intention(source,phase7=True,phase6_entry="f",phase6_examples=(Example((4,),3),))
    assert len(result.candidates) == 2
    assert all(c.compiler_valid and len(c.proposal.edits)==1 and "return pass(" in c.proposed_code for c in result.candidates)
    assert not analyze_intention(source,phase7=True).candidates


def test_guided_input_generation_respects_types_and_supplied_arguments():
    pair = [prepare(source) for source in (SUBTRACTION,ADDITION)]
    rows = guided_inputs(pair,"f",((2,),))
    assert len(rows) <= 8 and len({args for args,_ in rows}) == len(rows)
    assert (2,) not in {args for args,_ in rows} and (3,) in {args for args,_ in rows}
    for args, _ in rows:
        assert all(type(arg) is int for arg in args)


def test_static_examples_return_hypotheses_and_legacy_contract_is_unchanged():
    body = dict(code=SUBTRACTION, mode="examples",
                requirement={"function":"f", "examples":[{"args":[4], "expected_return":3}]})
    with isolated_client() as client:
        result = client.post("/v1/intention-analysis", json=body | {"engine_version":7})
        assert result.status_code == 200, result.text
        data = result.json()
        assert data["finding"] == data["guided_evidence"] == "POSSIBLE_REPAIR"
        assert data["behavioral_status"] == "ORACLE_UNAVAILABLE" and len(data["candidates"]) == 2
        assert client.post("/v1/intention-analysis", json=body | {"engine_version":65}).status_code == 422
        legacy = client.post("/v1/intention-analysis", json={"code":SUBTRACTION,"mode":"code_only","engine_version":65}).json()
        assert "guided_evidence" not in legacy


def test_disabled_gateway_and_observation_input_validation(monkeypatch):
    with isolated_client() as client:
        monkeypatch.delenv("INTENTFORGE_VM_GATEWAY", raising=False)
        payload = verify_payload(SUBTRACTION)
        assert client.post(URL, json=payload | {"actual":3}).status_code == 422
        assert client.post(URL, json=payload | {"language":"c"}).status_code == 422
        conflicting = payload | {"vectors": [payload["vectors"][0], {"arguments":[4], "expected":4}]}
        assert client.post(URL, json=conflicting).status_code == 422
        disabled = client.post(URL,json=payload).json()
        assert disabled["availability"]["status"] == "disabled"
        assert disabled["guided_evidence"]["original"] == "VERIFICATION_UNAVAILABLE"
        assert not disabled["guided_evidence"]["confirmed_fault"] and disabled["requires_approval"]
        legacy = client.post(URL,json=payload | {"engine_version":65}).json()
        assert not {"guided_evidence","candidate_pairs","candidate_categories"} & legacy.keys()


@pytest.mark.skipif(not os.getenv("INTENTFORGE_VM_SOCKET"), reason="Requires verified local Linux worker")
@pytest.mark.parametrize(("source", "expected", "n", "original", "review"), [
    (SUBTRACTION, 3, 4, "CONFIRMED_TEST_MISMATCH", "REVIEW_MATCHING_REPAIR"),
    (SUBTRACTION, -1, 4, "ORIGINAL_MATCHES_SUPPLIED_TESTS", "POSSIBLE_REPAIR"),
    (MULTIPLICATION, 1, 2, "CONFIRMED_TEST_MISMATCH", "MULTIPLE_PLAUSIBLE_REPAIRS"),
])
def test_isolated_guided_policy_retains_candidate_pool(source, expected, n, original, review):
    with isolated_client() as client:
        payload = verify_payload(source,expected,n)
        prior = client.post(URL,json=payload | {"engine_version":65}).json()
        current = client.post(URL,json=payload).json()
    assert current["availability"]["status"] == "available", current
    assert [row["id"] for row in current["candidates"]] == [row["id"] for row in prior["candidates"]]
    assert len(current["candidates"]) == 2 and current["requires_approval"]
    assert (current["guided_evidence"]["original"],current["guided_evidence"]["review"]) == (original,review)
    assert current["guided_evidence"]["confirmed_fault"] == (original == "CONFIRMED_TEST_MISMATCH")
    assert all("expected" not in probe for probe in current["probes"])
