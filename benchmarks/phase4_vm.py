"""Phase 4 fixture, reference-property, repair and recorded workbench evidence."""
import argparse
import json
from math import ceil, trunc
from pathlib import Path
from statistics import mean, median
from time import perf_counter

from ai.behavior_oracle import ExecutionLimits, Status
from ai.correction_safety import repair_key
from vm.behavioral_executor import MiniCOracle
from vm.repair_verification import analyze_with_behavior

from .phase4_cases import REPAIRS, SEMANTICS, vectors

ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / "benchmarks/reports/phase4-vm-v1.json"
DEMOS = ROOT / "frontend/src/data/phase4-demonstrations.json"
PROVENANCE = "Project-authored trusted Mini-C examples executed by the Phase 4 interpreter"


def elapsed(fn):
    start = perf_counter()
    value = fn()
    return value, (perf_counter() - start) * 1000


def timing(values):
    ordered = sorted(values)
    return {"mean": mean(ordered), "p95": ordered[ceil(len(ordered) * .95) - 1]}


def same(result):
    return result.model_dump(mode="json")


def sample(result):
    detail = result.execution
    return {"steps": [row.steps for row in detail.samples],
            "peak_cells": max((row.peak_cells for row in detail.samples), default=0),
            "max_call_depth": max((row.call_depth for row in detail.samples), default=0),
            "trace_entries": len(detail.trace), "trace_truncated": detail.trace_truncated,
            "trace_bytes": len(json.dumps([same(event) for event in detail.trace], separators=(",", ":")).encode())}


def reference_check():
    # Small integers make the Python floating division reference exact enough
    # for truncation. Remainder is independently checked by q*b+r == a.
    oracle = MiniCOracle()
    count = 0
    for a in range(-4, 5):
        values = [((a, b), trunc(a / b)) for b in range(-4, 5) if b]
        for operator, expected in (
            ("/", values), ("%", [((x, y), x - y*q) for (x, y), q in values]),
        ):
            result = oracle.verify(f"int f(int a,int b){{return a{operator}b;}}", "f", vectors(*expected), ExecutionLimits())
            assert result.status == Status.MATCHES_SUPPLIED_TESTS
            count += len(expected)
    return count


def run():
    plain = MiniCOracle()
    traced = MiniCOracle(trace=True)
    plain.verify(SEMANTICS[0].source, "f", SEMANTICS[0].vectors, ExecutionLimits())
    semantic, repair, display = [], [], []
    for case in SEMANTICS:
        plain_times, trace_times = [], []
        for _ in range(5):
            result, ms = elapsed(lambda: plain.verify(case.source, "f", case.vectors, case.limits))
            trace, trace_ms = elapsed(lambda: traced.verify(case.source, "f", case.vectors, case.limits))
            plain_times.append(ms)
            trace_times.append(trace_ms)
        ms, trace_ms = median(plain_times), median(trace_times)
        assert result.status == trace.status == case.status
        assert result.observations == trace.observations
        assert (result.execution.issue.code if result.execution.issue else None) == case.issue
        assert trace == traced.verify(case.source, "f", case.vectors, case.limits)
        semantic.append({"family": case.family, "status": result.status, "issue": case.issue,
                         "observations": len(result.observations), "vectors": len(case.vectors),
                         "attempted_vectors": len(result.execution.samples),
                         "ms": ms, "trace_ms": trace_ms, **sample(trace)})
        if case.family in {"divide-by-zero", "bounded-loop"}:
            display.append({"id": case.family,
                            "label": "Division by zero" if case.issue == "DIVISION_BY_ZERO" else "Step limit",
                            "source": case.source, "original": same(trace), "candidates": [],
                            "comparison_status": "NO_OBSERVED_MATCH", "skipped_candidates": 0})
    for case in REPAIRS:
        (result, comparison), ms = elapsed(lambda: analyze_with_behavior(
            case.source, case.requirement(), ExecutionLimits(), trace=True,
        ))
        proposals = {choice.id: choice for choice in result.candidates}
        keys = [repair_key(choice.proposed_code) for choice in result.candidates]
        target = repair_key(case.accepted) if case.accepted else None
        first = keys.index(target) + 1 if target in keys else None
        rows = [{"id": row.id, "static_rank": row.static_rank, "proposed_code": proposals[row.id].proposed_code,
                 "behavior": same(row.behavior)}
                for row in comparison.candidates]
        repair.append({"family": case.family, "references": int(target is not None), "first_match_rank": first,
                       "candidate_count": len(keys), "compiler_valid": sum(row.compiler_valid for row in result.candidates),
                       "original_status": comparison.original.status, "executed_candidates": len(rows),
                       "passing": len(comparison.passing), "runtime_errors": sum(
                           row.behavior.status == Status.BEHAVIOR_UNKNOWN for row in comparison.candidates),
                       "different_test_passing_reference": sum(
                           repair_key(proposals[key].proposed_code) != target for key in comparison.passing) if target else 0,
                       "passing_accepted_reference": bool(target and any(
                           repair_key(proposals[key].proposed_code) == target for key in comparison.passing)),
                       "multiple_matches": comparison.status == "MULTIPLE_MATCHES",
                       "steps": sum(sum(sample(row.behavior)["steps"]) for row in comparison.candidates)
                       + sum(sample(comparison.original)["steps"]),
                       "requires_approval": comparison.requires_approval, "ms": ms})
        if case.family in {"doubling-requirement", "coincident-arguments"}:
            display.insert(0 if case.family == "doubling-requirement" else 1, {
                "id": case.family, "label": "Repair comparison" if case.family == "doubling-requirement" else "Ambiguous alternatives",
                "source": case.source, "original": same(comparison.original), "candidates": rows,
                "comparison_status": comparison.status, "skipped_candidates": comparison.skipped_candidates,
            })
    assert all(row["requires_approval"] for row in repair)
    assert any(row["multiple_matches"] for row in repair)
    assert any(row["runtime_errors"] for row in repair)
    return {
        "provenance": PROVENANCE, "semantic": semantic, "repairs": repair, "python_reference_vectors": reference_check(),
        "latency": {"plain_ms": timing([row["ms"] for row in semantic]),
                    "trace_ms": timing([row["trace_ms"] for row in semantic]),
                    "per_attempted_vector_ms": timing([row["ms"] / row["attempted_vectors"] for row in semantic if row["attempted_vectors"]]),
                    "repair_comparison_ms": timing([row["ms"] for row in repair])},
    }, display


def stable(result):
    return {**result, "latency": None, **{
        section: [{key: value for key, value in row.items() if key not in {"ms", "trace_ms"}} for row in result[section]]
        for section in ("semantic", "repairs")
    }}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    modes = parser.add_mutually_exclusive_group(required=True)
    modes.add_argument("--write", action="store_true")
    modes.add_argument("--check", action="store_true")
    options = parser.parse_args()
    result, demos = run()
    if options.write:
        REPORT.write_text(json.dumps(result, indent=2) + "\n")
        DEMOS.parent.mkdir(parents=True, exist_ok=True)
        DEMOS.write_text(json.dumps(demos, indent=2) + "\n")
    elif stable(result) != stable(json.loads(REPORT.read_text())) or demos != json.loads(DEMOS.read_text()):
        raise SystemExit("Phase 4 benchmark or recorded demonstration evidence changed.")
    print(f"Checked {len(SEMANTICS)} semantic families, {result['python_reference_vectors']} reference vectors "
          f"and {len(REPAIRS)} repair families.")
