"""Reviewed semantics, resource ceilings and trusted comparison tests."""

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from ai.behavior_oracle import BehaviorResult, ExecutionLimits, Status, Vector
from ai.intention_context import Example, Requirement
from ai.intention_engine import analyze_intention
from backend.app.main import app
from vm.behavioral_executor import MiniCOracle
from vm.repair_verification import verify_repairs
from vm.runtime import WorkBudget


def run(source, expected=0, args=(), *, limits=None, trace=False, oracle=None):
    return (oracle or MiniCOracle(trace=trace)).verify(
        source, "f", (Vector(arguments=args, expected=expected),), limits or ExecutionLimits(),
    )


@pytest.mark.parametrize(("body", "expected"), [
    ("return (3+4)*2-1;", 13),
    ("return -7/3;", -2),
    ("return -7%3;", -1),
    ("return 7%-3;", 1),
    ("return -2147483648;", -2147483648),
    ("int x=2;int y=(x+=3);return y+x++;", 10),
    ("int x=2;int y=++x;return y*10+x--;", 33),
    ("int x=2;{int x=5;x*=3;}return x;", 2),
    ("int x=0;for(int i=0;i<6;i++){if(i==1){continue;}if(i==4){break;}x+=i;}return x;", 5),
    ("int x=0;while(x<8){x++;if(x==3){return x;}}return 9;", 3),
    ("int a[3];int i=0;a[i++]=7;a[1]=3;a[0]+=a[1];return a[0]*10+i;", 101),
    ("int n=2;int a[n+1];a[2]=9;return a[2];", 9),
    ("int n=0;for(int i=0;i<2;i++){for(int j=0;j<3;j++){n+=i+j;}}return n;", 9),
    ("for(;;){return 4;}", 4),
    ("int a=1;int b=(a=3)+(a=5);return a*10+b;", 58),
])
def test_reviewed_integer_semantics(body, expected):
    result = run("int f(){" + body + "}", expected)
    assert result.status == Status.MATCHES_SUPPLIED_TESTS
    assert result.observations[0].actual == expected


@pytest.mark.parametrize(("source", "arguments", "answer"), [
    ("bool f(bool x){return !x && (3>=2);}", (False,), True),
    ("bool f(){return true || (1/0==0);}", (), True),
    ("bool f(){return false && (1/0==0);}", (), False),
    ("bool f(){bool a[2];a[1]=true;return a[1]==true;}", (), True),
    ("int pair(int a,int b){return a*10+b;}int f(){int n=2;return pair(n++,n++);}", (), 23),
    ("int f(int n){if(n==0){return 1;}return n*f(n-1);}", (5,), 120),
    ("int g=4;int read(){return g;}int f(){int g=9;return read();}", (), 4),
    ("int g;void change(){g=5;return;}int f(){change();return g;}", (), 5),
    ("int g[3];int f(){return g[2];}", (), 0),
])
def test_calls_globals_and_booleans(source, arguments, answer):
    assert run(source, answer, arguments).status == Status.MATCHES_SUPPLIED_TESTS


@pytest.mark.parametrize(("source", "status", "code"), [
    ("int f(){return 3/0;}", Status.BEHAVIOR_UNKNOWN, "DIVISION_BY_ZERO"),
    ("int f(){return -2147483648/-1;}", Status.BEHAVIOR_UNKNOWN, "INTEGER_OVERFLOW"),
    ("int f(){return 2147483647+1;}", Status.BEHAVIOR_UNKNOWN, "INTEGER_OVERFLOW"),
    ("int f(){int a[2];return a[-1];}", Status.BEHAVIOR_UNKNOWN, "ARRAY_BOUNDS"),
    ("int f(){int a[2];return a[2];}", Status.BEHAVIOR_UNKNOWN, "ARRAY_BOUNDS"),
    ("int f(){int a[2];return a[0];}", Status.BEHAVIOR_UNKNOWN, "UNINITIALIZED_VALUE"),
    ("int f(){int i;return i;}", Status.BEHAVIOR_UNKNOWN, "UNINITIALIZED_VALUE"),
    ("int f(){int a[0];return 0;}", Status.BEHAVIOR_UNKNOWN, "INVALID_ARRAY_SIZE"),
    ("int f(){int a=1;}", Status.BEHAVIOR_UNKNOWN, "MISSING_RETURN"),
    ("int f(){return absent;}", Status.EXECUTION_UNSUPPORTED, "COMPILER_INVALID"),
    ("int g(){return 0;}", Status.EXECUTION_UNSUPPORTED, "MISSING_ENTRY"),
    ("int f(){if(false){float x=2.0;}return 0;}", Status.EXECUTION_UNSUPPORTED, "UNSUPPORTED_CONSTRUCT"),
    ("int f(){if(false) int x=0;return 0;}", Status.EXECUTION_UNSUPPORTED, "UNSUPPORTED_CONSTRUCT"),
    ("void f(){return;}", Status.EXECUTION_UNSUPPORTED, "UNSUPPORTED_ENTRY"),
    ("int f(){while(true){}}", Status.EXECUTION_LIMITED, "STEP_LIMIT"),
    ("int f(){return f();}", Status.EXECUTION_LIMITED, "CALL_DEPTH"),
    ("int f(){int a[20000];return 1;}", Status.EXECUTION_LIMITED, "MEMORY_CELLS"),
])
def test_structured_failures(source, status, code):
    result = run(source, trace=True)
    assert result.status == status
    assert result.execution.issue.code == code
    assert not result.observations


def test_clean_runs_and_deterministic_replay():
    oracle = MiniCOracle(trace=True)
    source = "int state=4;int f(){return ++state;}"
    vectors = (Vector(arguments=(), expected=5),) * 2
    first = oracle.verify(source, "f", vectors, ExecutionLimits())
    second = oracle.verify(source, "f", vectors, ExecutionLimits())
    assert first == second
    assert [row.actual for row in first.observations] == [5, 5]


def test_scope_storage_is_released_between_iterations():
    src = "int f(){for(int j=0;j<20;j++){int arr[3];arr[0]=j;}return 7;}"
    result = run(src, 7, limits=ExecutionLimits(memory_cells=5))
    assert result.status == Status.MATCHES_SUPPLIED_TESTS
    assert result.execution.samples[0].peak_cells == 5


def test_trace_budget_and_absolute_locations():
    source = "int f(){ /* 😀 */ int i=0;while(i<100){i++;}return i;}"
    result = run(source, 100, trace=True)
    trace = result.execution.trace
    assert result.execution.trace_truncated
    assert 1 <= len(trace) <= 64
    assert len(("[" + ",".join(row.model_dump_json() for row in trace) + "]").encode()) <= 8192
    declaration = next(row for row in trace if row.kind == "DECLARATION")
    prefix = source.split("int i")[0]
    assert declaration.span.start.byte_offset == len(prefix.encode())
    assert declaration.span.start.column == len(prefix.encode("utf-16-le")) // 2 + 1


def test_total_budget_size_and_call_depth_are_independent():
    oracle = MiniCOracle(budget=WorkBudget(5))
    limited = run("int f(){for(;;);}", oracle=oracle)
    assert limited.execution.issue.code == "VERIFICATION_BUDGET"
    assert run(" " * 24_001).execution.issue.code == "SOURCE_LIMIT"
    deep = run("int f(){return f();}", limits=ExecutionLimits(call_depth=128))
    assert deep.execution.issue.code == "CALL_DEPTH"
    assert deep.execution.samples[0].call_depth == 128


def test_vector_admission_and_actual_mismatches():
    oracle = MiniCOracle()
    source = "bool f(int v){return v==3;}"
    wrong_type = run(source, True, (False,))
    assert wrong_type.execution.issue.code == "INVALID_VECTOR"
    cases = (Vector(arguments=(3,), expected=True), Vector(arguments=(4,), expected=True))
    result = oracle.verify(source, "f", cases, ExecutionLimits())
    assert result.status == Status.MISMATCHES_SUPPLIED_TESTS
    assert [row.actual for row in result.observations] == [True, False]
    assert oracle.verify(source, "f", cases * 7, ExecutionLimits()).status == Status.EXECUTION_LIMITED
    assert oracle.verify(source, "f", (), ExecutionLimits()).status == Status.ORACLE_UNAVAILABLE


def test_partial_observations_do_not_count_as_success():
    oracle = MiniCOracle()
    result = oracle.verify("int f(int n){return 10/n;}", "f",
                           (Vector(arguments=(2,), expected=5), Vector(arguments=(0,), expected=0)),
                           ExecutionLimits())
    assert result.status == Status.BEHAVIOR_UNKNOWN
    assert [row.actual for row in result.observations] == [5]
    assert result.execution.issue.vector == 1
    with pytest.raises(ValidationError):
        data = result.model_dump()
        BehaviorResult.model_validate({**data, "status": Status.MATCHES_SUPPLIED_TESTS})


def test_trusted_repair_runs_keep_static_order_and_approval():
    requirement = Requirement(function="f", return_expression="x*2", examples=(Example((4,), 8),))
    result = analyze_intention("int f(int x){return x+2;}", requirement, phase35=True)
    old_order = [item.id for item in result.candidates]
    comparison = verify_repairs(result, ExecutionLimits(), trace=True)
    assert comparison.original.observations[0].actual == 6
    assert comparison.candidates[0].behavior.observations[0].actual == 8
    assert comparison.passing and comparison.requires_approval
    assert [item.id for item in result.candidates] == old_order
    candidate = result.to_dict()["candidates"][0]
    assert candidate["safety"]["requires_review"]
    assert candidate["behavioral_status"] == "MATCHES_SUPPLIED_TESTS"
    wrong = comparison.candidates[0].behavior.model_copy(update={"candidate_id": "stale"})
    with pytest.raises(ValueError, match="snapshot"):
        result.record_behavior(wrong)


def test_multiple_fixes_are_not_disambiguated_by_coincident_values():
    requirement = Requirement(function="choose", examples=(Example((2, 2), 2),))
    result = analyze_intention("int choose(int a,int b){return lost;}", requirement, phase35=True)
    comparison = verify_repairs(result, ExecutionLimits())
    assert comparison.original.status == Status.EXECUTION_UNSUPPORTED
    assert comparison.status == "MULTIPLE_MATCHES" and len(comparison.passing) == 2
    assert comparison.requires_approval and result.decision == "AMBIGUOUS"


def test_default_intention_does_not_execute_and_public_injection_is_rejected():
    client = TestClient(app)
    source = "int f(){for(;;);}"
    payload = {"code": source}
    assert client.post("/v1/intention-analysis", json=payload).json()["behavioral_status"] == "ORACLE_UNAVAILABLE"
    assert client.post("/v1/intention-analysis", json={**payload, "behavioral_evidence": {}}).status_code == 422
    assert client.post("/v1/execute", json=payload).status_code == 404
    assert client.post("/v1/verify-repairs", json=payload).status_code == 404
    c_context = analyze_intention("struct P { int n; };", Requirement(function="f", examples=(Example((), 0),)))
    assert verify_repairs(c_context, ExecutionLimits()).status == "EXECUTION_UNSUPPORTED"


def test_identity_requires_original_source_and_exact_typed_vectors():
    source = "bool f(bool flag){return flag;}"
    result = analyze_intention(source, Requirement(function="f", examples=(Example((True,), True),)))
    oracle = MiniCOracle()
    stale = oracle.verify(source + "\n", "f", (Vector(arguments=(True,), expected=True),), ExecutionLimits())
    with pytest.raises(ValueError, match="snapshot"):
        result.record_behavior(stale)
    wrong = oracle.verify(source, "f", (Vector(arguments=(False,), expected=False),), ExecutionLimits())
    with pytest.raises(ValueError, match="exact supplied vectors"):
        result.record_behavior(wrong)


def test_reverification_clears_skipped_evidence_and_releases_candidate_budget(monkeypatch):
    from vm import repair_verification

    source = "int f(int a){return a+2;}"
    result = analyze_intention(source, Requirement(function="f", return_expression="a*2",
                                                   examples=(Example((4,), 8),)), phase35=True)
    assert verify_repairs(result, ExecutionLimits()).passing
    monkeypatch.setattr(repair_verification, "ORACLE_STEPS", 1)
    repeated = verify_repairs(result, ExecutionLimits())
    assert repeated.original.status == Status.EXECUTION_LIMITED
    assert repeated.skipped_candidates == len(result.candidates)
    assert not repeated.candidates and all(choice.behavior is None for choice in result.candidates)


def test_each_step_and_live_cell_limit_has_an_exact_boundary():
    source = "int f(){int a[4];a[1]=7;return a[1];}"
    recorded = run(source, 7).execution.samples[0]
    enough = run(source, 7, limits=ExecutionLimits(steps=recorded.steps, memory_cells=recorded.peak_cells))
    assert enough.status == Status.MATCHES_SUPPLIED_TESTS
    step = run(source, 7, limits=ExecutionLimits(steps=recorded.steps - 1))
    assert step.execution.issue.code == "STEP_LIMIT"
    memory = run(source, 7, limits=ExecutionLimits(memory_cells=recorded.peak_cells - 1))
    assert memory.execution.issue.code == "MEMORY_CELLS"


def test_example_only_verification_preserves_code_only_boundary_hypotheses():
    from vm.repair_verification import analyze_with_behavior

    source = "int v[6];int f(){for(int k=3;k>=-1;k--){v[k]=k;}return v[2];}"
    result, compared = analyze_with_behavior(source, Requirement(function="f", examples=(Example((), 2),)),
                                            ExecutionLimits())
    assert compared.original.execution.issue.code == "ARRAY_BOUNDS"
    assert len(compared.passing) == 1
    assert result.candidates[0].proposed_code == source.replace("k>=-1", "k>-1")
    assert result.candidates[0].to_dict(source, False)["safety"]["requires_review"]


def test_review_order_can_promote_a_passing_candidate_within_the_fixed_run_cap():
    source = "int f(int x){return x+9;}"
    examples = (Example((4,), 12),)
    targets = ("x + 1", "x * 3", "x - 2", "x + 7", "x * 4")
    alternatives = [analyze_intention(source, Requirement(function="f", return_expression=expression,
                                                            examples=examples), phase35=True)
                    for expression in targets]
    result = alternatives[0]
    result.candidates = [entry.candidates[0] for entry in alternatives]
    old_order = tuple(choice.id for choice in result.candidates)
    compared = verify_repairs(result, ExecutionLimits())
    assert compared.original.status == Status.MISMATCHES_SUPPLIED_TESTS
    assert len(compared.candidates) == 4 and compared.skipped_candidates == 1
    assert compared.review_order == (old_order[1], old_order[0], *old_order[2:])
    assert tuple(choice.id for choice in result.candidates) == old_order
    assert result.candidates[-1].behavior is None and compared.requires_approval


def test_unexpected_internal_error_does_not_expose_source_or_claim_success(monkeypatch, caplog):
    from vm import behavioral_executor

    def fail(source):
        raise RuntimeError("private fixture text: " + source)
    monkeypatch.setattr(behavioral_executor, "prepare", fail)
    result = run("int f(){int private_marker=1;return private_marker;}")
    assert result.status == Status.BEHAVIOR_UNKNOWN and not result.observations
    assert result.execution.issue.code == "INTERNAL_FAILURE"
    assert "private_marker" not in result.model_dump_json() + caplog.text
