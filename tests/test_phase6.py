"""Independent tests for semantic analysis, synthesis, and worker-compatible review."""
import os
from time import monotonic

from fastapi.testclient import TestClient
import pytest

from ai.behavior_oracle import ExecutionLimits, Status, Vector, program_identity
from ai.intention_context import Example, build_context
from ai.intention_engine import analyze_intention
from analysis_evidence.function_summary import analyze_program, summaries
from backend.app.main import app
from vm.behavioral_executor import MiniCOracle

RECURSIVE = "int f(int n){if(n<=0){return 0;}return 2+f(n);}"
BOUNDARY = "int f(int n){if(n==1){return 2;}return 2+f(n-1);}"
RETURN_CHAIN = "int f(int n,bool q){int raw=n+2;int scaled=raw*3;int adjusted=scaled+5;if(q){return raw;}return raw;}"


def inspect(source):
    context = build_context(source)
    analysis = analyze_program(context, monotonic()+1)
    assert analysis.status == "AVAILABLE"
    return analysis, summaries(context, analysis, include_graph=True)


def test_cfg_distinguishes_nested_break_continue_and_literal_dead_branch():
    text = "int f(int n){for(int i=0;i<n;i++){while(true){if(i==1){continue;}break;}continue;}if(false){return 99;}return n;}"
    result, report = inspect(text)
    row, = report["functions"]
    by_id = {block["id"]: block for block in row["cfg"]["blocks"]}
    edges = row["cfg"]["edges"]
    assert sum(edge["kind"] == "back" for edge in edges) == 2
    targets = {edge["target"] for edge in edges if edge["kind"] == "continue"}
    assert len(targets) == 2 and all(by_id[target]["kind"] == "loop_latch" for target in targets)
    break_edge, = (edge for edge in edges if edge["kind"] == "break")
    assert by_id[break_edge["target"]]["kind"] == "continue"
    assert sum(block["kind"] == "return" and not block["reachable"] for block in by_id.values()) == 1
    assert result.functions[0].reachable == result.functions[0].flow.graph.reachable()


def test_reaching_definitions_merge_paths_preserve_scope_and_loop_carried_sites():
    source = "int f(bool flag,int k){int s=1;if(flag){s=2;}{int s=40;s++;}while(k>0){s+=k;k--;}return s;}"
    analysis, report = inspect(source)
    item, = analysis.functions
    row, = report["functions"]
    returned, = row["returns"]
    outer = next(binding for binding in item.flow.graph.blocks if binding.kind == "return")
    original = next(symbol.id for symbol in analysis.bindings.symbols.values() if symbol.name == "s")
    assert {definition["binding"] for definition in returned["definitions"] if definition["name"] == "s"} == {original}
    reaching = item.flow.for_binding(outer.id, original)
    assert len(reaching) == 3
    assert any(definition["name"] == "k" for definition in returned["definitions"])


def test_unknown_global_and_arrays_are_possible_writes_and_mutual_cycles_are_visible():
    source = """int data[4];int count=0;
      int f(int n){if(n<=0){return count;}data[n]=n;return partner(n-1);}
      int partner(int n){if(n<=0){return 1;}count++;return f(n-1);}
      int partial(int n){if(n>1){return n;}}"""
    analysis, report = inspect(source)
    f, partner, partial = report["functions"]
    assert (f["recursion"], partner["recursion"]) == ("MUTUAL", "MUTUAL")
    assert f["calls"] == ["partner"] and partial["possible_missing_return"]
    global_ids = analysis.bindings.globals
    assert global_ids <= set(f["possible_writes"])
    assert "array_cells_merged" in f["effects"]
    assert not any(item.proposal.category == "RECURSIVE_ARGUMENT_UPDATE"
                   for item in analyze_intention(source, phase6=True).candidates)


@pytest.mark.parametrize("guard", ["i < n", "n > i", "!(i >= n)", "!(n <= i)"])
def test_pure_comparison_orientation_gives_same_loop_evidence_and_vm_result(guard):
    source = "int f(int n){int tally=0;int total=0;for(int i=0;" + guard + ";tally++){total+=i;}return total;}"
    result = analyze_intention(source, phase6=True)
    assert result.program_analysis["status"] == "AVAILABLE"
    candidate, = [item for item in result.candidates if item.proposal.category == "LOOP_PROGRESS_BINDING"]
    assert candidate.compiler_valid and ";i++)" in candidate.proposed_code
    vectors = tuple(Vector(arguments=(n,), expected=n*(n-1)//2) for n in (0, 2, 5))
    assert MiniCOracle().verify(candidate.proposed_code, "f", vectors, ExecutionLimits()).status == Status.MATCHES_SUPPLIED_TESTS


@pytest.mark.parametrize("guard", ["i++ < n", "i + 1 < n", "i < helper(n)", "i < a[0]"])
def test_normalization_refuses_effectful_or_fault_capable_operands(guard):
    text = "int helper(int n){return n;}int f(int n){int a[1];int i=0;if(" + guard + "){return 3;}return 1;}"
    _, report = inspect(text)
    assert report["functions"][1]["conditions"][0]["normalized"] is None


def test_recursive_proposal_is_structural_and_limits_are_distinct_from_mismatch():
    result = analyze_intention(RECURSIVE, phase6=True)
    candidate, = result.candidates
    assert candidate.proposal.category == "RECURSIVE_ARGUMENT_UPDATE"
    assert "f(n - 1)" in candidate.proposed_code
    cases = tuple(Vector(arguments=(n,), expected=2*n) for n in (0, 1, 4))
    oracle = MiniCOracle()
    original = oracle.verify(RECURSIVE, "f", cases, ExecutionLimits())
    assert original.status == Status.EXECUTION_LIMITED and original.execution.issue.code == "CALL_DEPTH"
    fixed = oracle.verify(candidate.proposed_code, "f", cases, ExecutionLimits())
    assert fixed.status == Status.MATCHES_SUPPLIED_TESTS


def test_singleton_base_requires_domain_and_result_examples():
    assert not analyze_intention(BOUNDARY, phase6=True).candidates
    result = analyze_intention(BOUNDARY, phase6=True, phase6_entry="f",
                               phase6_examples=(Example((0,), 2), Example((1,), 3)))
    choices = {candidate.proposal.category: candidate for candidate in result.candidates}
    assert set(choices) == {"BASE_CASE_BOUNDARY", "BASE_CASE_RETURN"}
    assert "|| n == 0" in choices["BASE_CASE_BOUNDARY"].proposed_code
    assert "return 3;" in choices["BASE_CASE_RETURN"].proposed_code
    assert all(item.compiler_valid for item in choices.values())


def test_multi_return_repair_has_two_spans_and_snapshot():
    result = analyze_intention(RETURN_CHAIN, phase6=True)
    candidate, = result.candidates
    assert candidate.proposal.category == "RETURN_DEPENDENCY_MISMATCH"
    assert len(candidate.proposal.edits) == 2 and candidate.proposed_code.count("return adjusted;") == 2
    row, = result.to_dict()["candidates"]
    assert row["source_snapshot"] == program_identity(RETURN_CHAIN) and row["requires_approval"]
    assert row["counter_evidence"]
    vectors = tuple(Vector(arguments=(n,q), expected=(n+2)*3+5) for n,q in [(4,True),(-1,False)])
    assert MiniCOracle().verify(candidate.proposed_code, "f", vectors, ExecutionLimits()).status == Status.MATCHES_SUPPLIED_TESTS


@pytest.mark.parametrize("source", [
    RETURN_CHAIN.replace("return raw;}return raw", "return adjusted;}return raw"),
    RETURN_CHAIN.replace("if(q)", "raw++;if(q)"),
    RETURN_CHAIN.replace("int adjusted=scaled+5;", "int adjusted=scaled+5;int alternative=scaled-7;"),
])
def test_return_abstention_with_distinct_paths_mutated_old_or_ambiguous_terminal(source):
    assert not any(item.proposal.category == "RETURN_DEPENDENCY_MISMATCH"
                   for item in analyze_intention(source, phase6=True).candidates)


def test_cfg_graph_limit_is_explicit_and_legacy_contract_is_unchanged():
    big = "int f(){int x=1;" + "x++;"*240 + "return x;}"
    limited = analyze_intention(big, phase6=True)
    assert limited.program_analysis["status"] == "ANALYSIS_LIMITED"
    local = TestClient(app)
    payload = {"code": RECURSIVE, "mode": "code_only", "include_context": True}
    phase55, phase6 = [local.post("/v1/intention-analysis", json={**payload, "engine_version": version}).json()
                       for version in (55,6)]
    assert "program_analysis" not in phase55
    assert phase6["program_analysis"]["functions"][0]["cfg"]["edges"]
    unsupported = local.post("/v1/intention-analysis", json={**payload, "engine_version": 6,
                              "code": "int f(bool q){if(q)int a=1;return 0;}"})
    assert unsupported.status_code == 422 and "control-body declarations" in unsupported.json()["detail"]


def test_behavior_gateway_keeps_recursion_isolated_and_evidence_review_only(monkeypatch):
    url = "/v1/behavioral-verification"
    request = {"source": RECURSIVE, "entry_point": "f", "engine_version": 6, "compare_candidates": True,
               "vectors": [{"arguments":[4], "expected":8}], "trace": True}
    with TestClient(app, base_url="http://127.0.0.1:8000", client=("127.0.0.1", 48590)) as client:
        assert client.post(url, json={**request, "actual":8}).status_code == 422
        if os.getenv("INTENTFORGE_VM_SOCKET"):
            reply = client.post(url, json=request).json()
            assert reply["availability"]["status"] == "available"
            assert reply["original"]["execution"]["issue"]["code"] == "CALL_DEPTH"
            assert reply["comparison_status"] == "ONE_MATCH" and reply["requires_approval"]
            choice, = reply["candidates"]
            assert choice["behavior"]["observations"][0]["actual"] == 8
        monkeypatch.delenv("INTENTFORGE_VM_GATEWAY", raising=False)
        assert client.post(url, json=request).json()["availability"]["status"] == "disabled"
