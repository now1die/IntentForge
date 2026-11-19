"""Independent reference formulas and Phase 4.5 runtime regressions."""
from math import trunc
from random import Random

import pytest

from ai.behavior_oracle import ExecutionLimits, Status, Vector
from compiler.parser import parse
from vm.behavioral_executor import MiniCOracle
from vm.interpreter import Execution, Trace, interpret, prepare
from vm.runtime import RuntimeFault, WorkBudget


def test_seeded_signed_arithmetic_against_independent_reference():
    rng = Random(45019)
    oracle = MiniCOracle()
    sources = {op: f"int f(int a,int b){{return a{op}b;}}" for op in ("/", "%", "+", "-", "*")}
    for op, source in sources.items():
        for block in range(4):
            rows = []
            for _ in range(12):
                a, b = rng.randint(-200, 200), (rng.randint(-200, 200) or 1)
                quotient = trunc(a / b)
                expected = {"/": quotient, "%": a - b * quotient, "+": a + b, "-": a - b, "*": a * b}[op]
                rows.append(Vector(arguments=(a, b), expected=expected))
            result = oracle.verify(source, "f", tuple(rows), ExecutionLimits())
            assert result.status == Status.MATCHES_SUPPLIED_TESTS, (op, block, rows, result)


@pytest.mark.parametrize(("source", "expected"), [
    ("int next(){return 7;}int seed=next();int f(){return seed++;}", 7),
    ("int f(){int x=1;int a[2];a[x++]=x++;return a[1]*10+x;}", 23),
    ("int f(){int a=8;return a+=(a=3);}", 11),
    ("int f(){int x=0;for(int i=0;i<4;i++){for(int j=0;j<3;j++){if(j==1){continue;}if(i==2){break;}x++;}}return x;}", 6),
    ("int f(){int x=2;{int x=7;{int x=19;x--;}}return x;}", 2),
    ("int f(){bool a[2];a[0]=false;a[1]=true;if(a[0]&&(1/0==0)){return 0;}if(a[1]){return 3;}return 0;}", 3),
    ("int f(){return 2147483647 + (-2147483648);}", -1),
    ("int f(){return -2147483647 % 2147483647;}", 0),
])
def test_state_and_evaluation_order_reference_cases(source, expected):
    oracle = MiniCOracle(trace=True)
    vectors = (Vector(arguments=(), expected=expected),) * 2
    first = oracle.verify(source, "f", vectors, ExecutionLimits())
    assert first.status == Status.MATCHES_SUPPLIED_TESTS
    assert first == oracle.verify(source, "f", vectors, ExecutionLimits())


def test_fault_unwinds_lexical_cells_and_all_frames():
    source = "int child(int x){int data[8];return x/data[0];}int f(){int a=4;for(int j=0;j<5;j++){return child(a); }return a;}"
    prepared = prepare(source)
    execution = Execution(prepared, ExecutionLimits(), WorkBudget(200_000), Trace(None), 0)
    with pytest.raises(RuntimeFault) as failure:
        interpret(execution.start(prepared.functions["f"], ()))
    assert failure.value.code == "UNINITIALIZED_VALUE"
    assert execution.frames == [] and execution.live_cells == 0
    assert execution.peak_cells >= 12


def test_extreme_integer_lexeme_is_diagnostic_instead_of_internal_failure():
    source = "int f(){return " + "9" * 6000 + ";}"
    parsed = parse(source)
    assert any(item.code == "NUMERIC_LITERAL_OUT_OF_RANGE" and len(item.lexeme) == 64
               for item in parsed.lexical_errors)
    result = MiniCOracle().verify(source, "f", (Vector(arguments=(), expected=0),), ExecutionLimits())
    assert result.status == Status.EXECUTION_UNSUPPORTED
    assert result.execution.issue.code == "COMPILER_INVALID"


def test_recursive_and_iterative_accumulation_agree_with_closed_form():
    oracle = MiniCOracle()
    cases = tuple(Vector(arguments=(n,), expected=n * (n + 1) // 2) for n in range(12))
    for source in ("int f(int n){if(n<1){return 0;}return n+f(n-1);}",
                   "int f(int n){int s=0;for(int j=1;j<=n;j++){s+=j;}return s;}"):
        result = oracle.verify(source, "f", cases, ExecutionLimits())
        assert result.status == Status.MATCHES_SUPPLIED_TESTS
