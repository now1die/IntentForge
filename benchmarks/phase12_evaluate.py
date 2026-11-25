"""Replay Phase 12 components and separately verify independent holdout."""
import argparse
from collections import Counter
import json
from time import perf_counter

from ai.behavior_oracle import ExecutionLimits, Status, Vector
from ai.correction_safety import repair_key
from ai.intention_engine import analyze_intention
from vm.behavioral_executor import MiniCOracle

from .phase5_evaluate import fraction, latency
from .phase6_evaluate import REPORTS, URL
from .phase55_evaluate import stable
from .phase85_evaluate import measured_case, observed, run_projection
from .phase9_evaluate import candidate_signature
from .phase115_evaluate import archived_cases, nested_variations
from .phase115_fixtures import ROOT as PHASE115
from .phase12_audit import audit

PROFILES = {
    "105": {"phase105": True}, "11": {"phase11": True}, "115": {"phase115": True},
    "state": {"phase12": True, "phase12_components": frozenset()},
    **{component: {"phase12": True, "phase12_components": frozenset({component})}
       for component in ("logical", "initialization", "coordinate")},
    "12": {"phase12": True},
}


def suite(values):
    return tuple(Vector.model_validate(value) for value in values)


def execute(oracle, source, vectors, entry="f"):
    return oracle.verify(source, entry, vectors, ExecutionLimits())


def projection_row(oracle, case, settings):
    source = case["source"]
    discovery, holdout = suite(case["vectors"]), suite(case["holdout_vectors"])
    references = {repair_key(candidate) for candidate in case["references"]}
    start = perf_counter()
    result = run_projection(case, **settings)
    elapsed = 1000 * (perf_counter() - start)
    code_only = analyze_intention(source, **settings).candidates
    original = execute(oracle, source, discovery)
    original_final = execute(oracle, source, holdout)
    candidates = []
    for candidate, data in zip(result.candidates, result.to_dict()["candidates"], strict=True):
        proposed = candidate.proposed_code
        exact = repair_key(proposed) in references
        check = execute(oracle, proposed, discovery)
        final = execute(oracle, proposed, holdout) if check.status == Status.MATCHES_SUPPLIED_TESTS else None
        counterexamples = []
        if final and final.status != Status.MATCHES_SUPPLIED_TESTS:
            for test, observed_test in zip(holdout, final.observations):
                if observed_test.actual != test.expected or type(observed_test.actual) is not type(test.expected):
                    baseline = execute(oracle, source, (test,))
                    counterexamples.append({"input": list(test.arguments), "expected": test.expected,
                                            "original": baseline.observations[0].actual if baseline.observations else None,
                                            "original_issue": baseline.execution.issue.code if baseline.execution.issue else None,
                                            "actual": observed_test.actual})
            if final.execution.issue:
                issue = final.execution.issue
                if issue.vector is not None:
                    test = holdout[issue.vector]
                    baseline = execute(oracle, source, (test,))
                    counterexamples.append({"input": list(test.arguments), "expected": test.expected,
                                            "original": baseline.observations[0].actual if baseline.observations else None,
                                            "original_issue": baseline.execution.issue.code if baseline.execution.issue else None,
                                            "actual": None, "candidate_issue": issue.code})
        candidates.append({"id": data["id"], "category": candidate.proposal.category, "edits": len(candidate.proposal.edits),
                           "compiler_valid": candidate.compiler_valid, "exact": exact, "discovery": check.status,
                           "holdout": final.status if final else "NOT_RUN", "counterexamples": counterexamples})
    return {"id": case["id"], "origin": case["fault_origin"], "original": original.status,
            "original_issue": original.execution.issue.code if original.execution.issue else None,
            "original_holdout": original_final.status, "candidates": candidates,
            "code_only_exact": any(repair_key(candidate.proposed_code) in references for candidate in code_only),
            "code_only_behavioral": bool(references) and any(
                execute(oracle, candidate.proposed_code, (*discovery, *holdout)).status == Status.MATCHES_SUPPLIED_TESTS
                for candidate in code_only),
            "phase12_status": (result.program_analysis or {}).get("phase12", {}).get("status")}, elapsed


def metrics(rows):
    groups = {}
    for origin in ("adapted-real-defect", "authored-injected"):
        cases = [row for row in rows if row["origin"] == origin]
        candidates = [choice for row in cases for choice in row["candidates"]]
        passing = [[choice for choice in row["candidates"] if choice["holdout"] == Status.MATCHES_SUPPLIED_TESTS]
                   for row in cases]
        groups[origin] = {
            "exact": fraction(sum(any(choice["exact"] for choice in row) for row in passing), len(cases)),
            "behavioral": fraction(sum(bool(row) for row in passing), len(cases)),
            "generated": fraction(sum(bool(row["candidates"]) for row in cases), len(cases)),
            "compiler_valid": fraction(sum(choice["compiler_valid"] for choice in candidates), len(candidates)),
            "discovery": fraction(sum(choice["discovery"] == Status.MATCHES_SUPPLIED_TESTS for choice in candidates), len(candidates)),
            "holdout": fraction(sum(map(len, passing)), sum(choice["holdout"] != "NOT_RUN" for choice in candidates)),
            "code_only_exact": fraction(sum(row["code_only_exact"] for row in cases), len(cases)),
            "code_only_behavioral": fraction(sum(row["code_only_behavioral"] for row in cases), len(cases)),
            "ambiguous_discovery": fraction(sum(sum(choice["discovery"] == Status.MATCHES_SUPPLIED_TESTS
                                                   for choice in row["candidates"]) > 1 for row in cases), len(cases)),
        }
    controls = [row for row in rows if row["origin"] is None]
    return groups | {"controls_with_static_suggestions": fraction(sum(bool(row["candidates"]) for row in controls), len(controls))}


def metamorphic(oracle, cases, profile="phase12"):
    settings = {profile: True}
    changes, counts = [], Counter()
    for case in cases:
        source = case["source"]
        vectors = suite(case["vectors"])
        signature = candidate_signature(oracle, run_projection(case, **settings).candidates, "f", vectors)
        original = observed(execute(oracle, source, vectors))
        for name, variant, entry in nested_variations(source):
            counts[name] += 1
            result = run_projection(case, source=variant, entry=entry, **settings)
            revised = candidate_signature(oracle, result.candidates, entry, vectors)
            if observed(execute(oracle, variant, vectors, entry)) != original or revised != signature:
                changes.append({"case": case["id"], "transformation": name,
                                "before": sorted(signature.items(), key=repr), "after": sorted(revised.items(), key=repr)})
    return {"checks": dict(counts), "total": sum(counts.values()), "changes": changes}


def evaluate(cases):
    oracle = MiniCOracle()
    reports = {}
    for case in cases:
        suite_values = suite(case["vectors"] + case["holdout_vectors"])
        for code in case["references"] or [case["source"]]:
            assert execute(oracle, code, suite_values).status == Status.MATCHES_SUPPLIED_TESTS, case["id"]
    for name, settings in PROFILES.items():
        rows, durations = zip(*(projection_row(oracle, case, settings) for case in cases), strict=True)
        reports[name] = {"rows": list(rows), "metrics": metrics(rows), "latency": latency(durations)}
    archived = [case for case, _ in archived_cases()]
    retained = next(row for row in json.loads((PHASE115 / "cases-v1.json").read_text())
                    if row["id"] == "empty-retained-run-fault")
    archived.append(retained)
    archive = {profile: [projection_row(oracle, case, PROFILES[profile])[0] for case in archived]
               for profile in ("115", "12")}
    return {"profiles": reports, "archived": archive, "metamorphic": metamorphic(oracle, cases)}


def live(cases, versions=(105, 11, 115, 12)):
    from fastapi.testclient import TestClient
    from backend.app.main import app

    runs = {}
    with TestClient(app, base_url="http://127.0.0.1:8000", client=("127.0.0.1", 41712)) as client:
        assert client.get(URL + "/capability").json()["status"] == "available"
        for version in versions:
            rows, durations = [], []
            for case in cases:
                start = perf_counter()
                rows.append(measured_case(client, case, version))
                durations.append(1000 * (perf_counter() - start))
            by_kind = {}
            for kind in ("adapted-real-defect", "authored-injected", None):
                related = [row for case, row in zip(cases, rows, strict=True) if case["fault_origin"] == kind]
                tested = [choice for row in related for choice in row["holdout"]]
                recommended = [choice for choice in tested if choice["recommended"]]
                by_kind[kind or "controls"] = {
                    "holdout_behavioral": fraction(sum(any(choice["status"] == Status.MATCHES_SUPPLIED_TESTS
                                                          for choice in row["holdout"]) for row in related), len(related)),
                    "holdout_exact": fraction(sum(any(choice["exact"] and choice["status"] == Status.MATCHES_SUPPLIED_TESTS
                                                     for choice in row["holdout"]) for row in related), len(related)),
                    "confirmed": fraction(sum(row["policy"]["confirmed_fault"] for row in related), len(related)),
                    "recommendation": fraction(sum(row["policy"]["recommended_candidate"] is not None
                                                   for row in related), len(related)),
                    "abstention": fraction(sum(row["policy"]["recommended_candidate"] is None
                                               for row in related), len(related)),
                    "recommended_holdout_failure": fraction(sum(choice["status"] != Status.MATCHES_SUPPLIED_TESTS
                                                                 for choice in recommended), len(recommended)),
                    "speculative_candidates": sum(row["compiled"] for row in related) if kind is None else None,
                }
            runs[str(version)] = {"rows": rows, "metrics": by_kind, "latency": latency(durations),
                                 "max_discovery_steps": max(row["observed_steps"] + row["probe_steps"] for row in rows),
                                 "max_peak_cells": max(row["max_peak_cells"] for row in rows)}
    return runs


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--live", action="store_true")
    args = parser.parse_args()
    admitted, _ = audit()
    cases = [row for row in admitted if row["partition"] == "final"]
    report = json.loads(json.dumps(live(cases) if args.live else evaluate(cases)))
    if args.check:
        name = "live" if args.live else "static"
        assert stable(report) == stable(json.loads((REPORTS / f"phase12-{name}-v1.json").read_text()))
        print(f"Verified {len(cases)} Phase 12 final cases ({name}).")
    else:
        print(json.dumps(report, indent=2))
