"""New authored Mini-C semantic programs and a seeded mathematical reference."""
import argparse
import json
from math import ceil
from pathlib import Path
from random import Random
from statistics import mean, median
from time import perf_counter

from ai.behavior_oracle import ExecutionLimits, Status, Vector
from vm.behavioral_executor import MiniCOracle
from vm.interpreter import Execution, Trace, interpret, prepare
from vm.runtime import WorkBudget

ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / "benchmarks/reports/phase45-vm-v1.json"

PROGRAMS = (
    ("signed-reconstruction", "int f(int a,int b){return (a/b)*b + a%b;}", (17, -3), 17, None),
    ("bool-branch", "bool f(bool a,bool b){if(a){return !b;}return a||b;}", (True, False), True, None),
    ("continue-break", "int f(int stop){int sum=0;for(int i=0;i<10;i++){if(i==stop){break;}if(i%2==0){continue;}sum+=i;}return sum;}", (8,), 16, None),
    ("spectral-grid", "int f(){int s=0;for(int i=1;i<=3;i++){for(int j=2;j<=4;j++){s+=i*j;}}return s;}", (), 54, None),
    ("recursive-squared", "int g(int n){if(n<=0){return 0;}return n*n+g(n-1);}int f(int n){return g(n);}", (5,), 55, None),
    ("local-and-global", "int token=2;int read(){return token;}int f(){int token=7;{int token=11;token++;}return token*10+read();}", (), 72, None),
    ("array-index-side-effects", "int f(){int a[3];int i=0;a[i++]=i++;a[i]=7;return a[0]+a[2];}", (), 8, None),
    ("compound-read-first", "int f(){int price=25;return price-=(price=6);}", (), 19, None),
    ("global-init-call", "int value(){return 13;}int g=value();int f(){return g++;}", (), 13, None),
    ("runtime-overflow", "int f(){return (-2147483648)*2;}", (), 0, "INTEGER_OVERFLOW"),
    ("runtime-index", "int box[4];int f(int n){return box[n+1];}", (3,), 0, "ARRAY_BOUNDS"),
    ("loop-limit", "int f(){int n=3;while(true){n+=1;}}", (), 0, "STEP_LIMIT"),
    ("allocation-limit", "int f(){int a[1000];return 2;}", (), 0, "MEMORY_CELLS"),
    ("unsupported-argument-type", "int f(char c){return 5;}", (), 0, "UNSUPPORTED_CONSTRUCT"),
)


def timed(fn):
    start = perf_counter()
    result = fn()
    return result, (perf_counter() - start) * 1000


def summary(samples):
    ordered = sorted(samples)
    return {"mean": mean(ordered), "median": median(ordered), "p95": ordered[ceil(len(ordered)*.95)-1]}


def generated():
    # Bounded reference programs. Each vector is uniquely reproducible from
    # seed, operation and index. These ranges make all intermediates exact.
    rng = Random(451971)
    count = 0
    oracle = MiniCOracle()
    strings = (
        ("int f(int n){int total=0;for(int i=1;i<=n;i++){total+=i*2+1;} return total;}",
         lambda n: n*(n+2)),
        ("int f(int n){if(n<0){return -(n*n);}return n*n;}",
         lambda n: n*abs(n)),
        ("int f(int n){int v[1];v[0]=n++;v[0]*=++n;return v[0];}",
         lambda n: n*(n+2)),
    )
    for index, (source, reference) in enumerate(strings):
        for batch in range(6):
            rows = tuple(Vector(arguments=(value,), expected=reference(value))
                         for value in (rng.randint(-9 if index else 0, 16) for _ in range(12)))
            result = oracle.verify(source, "f", rows, ExecutionLimits())
            assert result.status == Status.MATCHES_SUPPLIED_TESTS, (index, batch, rows, result)
            count += len(rows)
    return count


def evaluate():
    oracle, trace = MiniCOracle(), MiniCOracle(trace=True)
    limits = ExecutionLimits(steps=600, memory_cells=100)
    prepare(PROGRAMS[0][1])
    records, prep, plain, traced, eval_only, fault = [], [], [], [], [], []
    for family, source, args, expected, error in PROGRAMS:
        vector = Vector(arguments=args, expected=expected)
        result, elapsed = timed(lambda: oracle.verify(source, "f", (vector, vector), limits))
        evidence, trace_ms = timed(lambda: trace.verify(source, "f", (vector, vector), limits))
        assert result.observations == evidence.observations and result.status == evidence.status
        assert evidence == trace.verify(source, "f", (vector, vector), limits)
        if error:
            assert evidence.execution.issue.code == error and not evidence.observations
            fault.append(elapsed)
        else:
            assert result.status == Status.MATCHES_SUPPLIED_TESTS and len(result.observations) == 2
            program, prep_ms = timed(lambda: prepare(source))
            prep.append(prep_ms)
            engine = Execution(program, limits, WorkBudget(200_000), Trace(None), 0)
            value, exec_ms = timed(lambda: interpret(engine.start(program.functions["f"], args)))
            assert value == expected
            eval_only.append(exec_ms)
        plain.append(elapsed)
        traced.append(trace_ms)
        samples = result.execution.samples
        records.append({"family": family, "observations": len(result.observations), "status": result.status,
                        "issue": error, "steps": [item.steps for item in samples],
                        "peak_cells": max((item.peak_cells for item in samples), default=0),
                        "call_depth": max((item.call_depth for item in samples), default=0),
                        "trace_entries": len(evidence.execution.trace),
                        "trace_truncated": evidence.execution.trace_truncated})
    return {"version": 1, "provenance": "Project-authored fixtures and independent mathematical formulas",
            "families": len(records), "supplied_vectors": 2 * len(records),
            "generated_seed": 451971, "generated_reference_vectors": generated(), "programs": records,
            "timings_ms": {name: summary(rows) for name, rows in {
                "prepare": prep, "execution_one_vector": eval_only, "verification": plain,
                "verification_with_trace": traced, "failure_handling": fault,
            }.items()}}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    modes = parser.add_mutually_exclusive_group(required=True)
    modes.add_argument("--write", action="store_true")
    modes.add_argument("--check", action="store_true")
    options = parser.parse_args()
    report = evaluate()
    if options.write:
        REPORT.write_text(json.dumps(report, indent=2) + "\n")
    elif {**report, "timings_ms": None} != {**json.loads(REPORT.read_text()), "timings_ms": None}:
        raise SystemExit("Phase 4.5 semantic evidence changed")
    print(f"Verified {report['families']} semantic families and {report['generated_reference_vectors']} seeded vectors.")
