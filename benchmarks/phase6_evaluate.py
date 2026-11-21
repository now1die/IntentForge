"""Reproduce Phase 6 semantic, same-pool and isolated verification outcomes."""
import argparse
from collections import Counter
from copy import copy
import json
import os
from pathlib import Path
from time import perf_counter, sleep

from ai.behavior_oracle import ExecutionLimits, Status, Vector
from ai.correction_safety import repair_key
from ai.intention_context import build_context
from ai.intention_engine import analyze_intention, order_candidates
from ai.intention_phase6 import CATEGORIES
from ai.intention_v3_ranker import load_generalized_ranker
from analysis_evidence.expression_normalization import REVERSE
from compiler import ast_nodes as ast
from vm.behavioral_executor import MiniCOracle

from .phase5_evaluate import fraction, latency
from .phase55_evaluate import stable, transformed
from .phase6_audit import audit

REPORTS = Path(__file__).with_name("reports")
ALERTS = {"COMPILER_ERROR", "HEURISTIC_SUSPICION", "SPECIFICATION_SUPPORTED_SUSPICION"}
URL = "/v1/behavioral-verification"


def vectors(case):
    return tuple(Vector.model_validate(item) for item in case["vectors"])


def rank(case, sources):
    references = {repair_key(text) for text in case["references"]}
    return next((i for i, code in enumerate(sources, 1) if repair_key(code) in references), None)


def independent_references(cases):
    oracle = MiniCOracle()
    for case in cases:
        if case["disposition"] == "ambiguous":
            continue
        for reference in case["references"] or [case["source"]]:
            result = oracle.verify(reference, "f", vectors(case), ExecutionLimits())
            assert result.status == Status.MATCHES_SUPPLIED_TESTS, (case["id"], result.status)
        if case["references"]:
            assert oracle.verify(case["source"], "f", vectors(case), ExecutionLimits()).status != Status.MATCHES_SUPPLIED_TESTS


def row(case, analysis, choices):
    return {
        "id": case["id"], "alert": analysis.finding in ALERTS,
        "rank": rank(case, [item.proposed_code for item in choices]),
        "attempts": analysis.attempts, "valid": sum(item.compiler_valid for item in choices),
        "candidates": len(choices), "duplicates": len(choices)-len({item.id for item in choices}),
        "categories": [item.proposal.category for item in choices],
        "recommendation": analysis.to_dict()["recommendation"],
        "learned_scored": sum(item.relative_score is not None for item in choices),
        "multi_site": sum(len(item.proposal.edits) > 1 for item in choices),
        "limited": bool(analysis.program_analysis and analysis.program_analysis["status"] != "AVAILABLE"),
    }


def metrics(cases, rows):
    paired = list(zip(cases, rows, strict=True))
    faults = [result for case, result in paired if case["references"]]
    controls = [result for case, result in paired if case["disposition"] == "control"]
    detected, false = sum(result["alert"] for result in faults), sum(result["alert"] for result in controls)
    return {
        "alerts": fraction(detected, len(faults)), "precision": fraction(detected, detected+false),
        "false_alerts": fraction(false, len(controls)),
        "recall": fraction(sum(result["rank"] is not None for result in faults), len(faults)),
        "top1": fraction(sum(result["rank"] == 1 for result in faults), len(faults)),
        "top3": fraction(sum(result["rank"] is not None and result["rank"] <= 3 for result in faults), len(faults)),
        "compiler_validity": fraction(sum(result["valid"] for result in rows), sum(result["candidates"] for result in rows)),
        "abstentions": sum(result["recommendation"] == "ABSTAIN" for result in rows),
        **{key: sum(result[key] for result in rows) for key in ("attempts", "duplicates", "multi_site", "limited", "learned_scored")},
    }


def static(cases, ranker):
    configurations = {name: [] for name in ("phase5", "phase55", "semantic_scan_without_generation",
                                              "phase6", "v4_same_pool", "pairwise_same_pool")}
    durations = []
    for case in cases:
        source = case["source"]
        prior = [("phase5", analyze_intention(source, phase5=True)),
                 ("phase55", analyze_intention(source, phase55=True)),
                 ("semantic_scan_without_generation", analyze_intention(source, phase6=True, phase6_generate=False))]
        start = perf_counter()
        current = analyze_intention(source, phase6=True)
        durations.append(1000*(perf_counter()-start))
        assert current.context.compiler_valid == case["compiler_valid"], case["id"]
        assert all(item.compiler_valid for item in current.candidates)
        for name, analysis in [*prior, ("phase6", current)]:
            configurations[name].append(row(case, analysis, analysis.candidates))
        for name, experiment in (("v4_same_pool", None), ("pairwise_same_pool", "pairwise")):
            other = order_candidates([copy(item) for item in current.candidates], None, expanded=ranker,
                                     generalized=True, experimental=experiment)
            assert {item.id for item in other} == {item.id for item in current.candidates}
            configurations[name].append(row(case, current, other))
    output = {"rows": configurations, "metrics": {key: metrics(cases, items) for key, items in configurations.items()}}
    if durations:
        output["latency"] = latency(durations)
    return output


def robustness(cases):
    engine = MiniCOracle()
    report = []
    for case in cases:
        if not case["compiler_valid"] or case["disposition"] == "ambiguous":
            continue
        source = case["source"]
        original = engine.verify(source, "f", vectors(case), ExecutionLimits())
        baseline = analyze_intention(source, phase6=True)
        before = sorted(item.proposal.category for item in baseline.candidates)
        for mode, revised, entry in safe_transforms(source):
            result = engine.verify(revised, entry, vectors(case), ExecutionLimits())
            assert original.status == result.status and [x.actual for x in original.observations] == [
                x.actual for x in result.observations], (case["id"], mode)
            analysis = analyze_intention(revised, phase6=True)
            assert analysis.context.compiler_valid
            assert all(0 <= edit.span.start.offset <= edit.span.end.offset <= len(revised)
                       for item in analysis.candidates for edit in item.proposal.edits)
            report.append({"id": case["id"], "transform": mode, "observation_equivalent": True,
                           "alerts_preserved": (analysis.finding in ALERTS) == (baseline.finding in ALERTS),
                           "categories_preserved": sorted(item.proposal.category for item in analysis.candidates) == before})
    return report


def safe_transforms(source):
    yield from (row for row in transformed(source) if row[0] != "reverse_comparison")
    context = build_context(source)
    conditions = [row.node.condition for kinds in ((ast.ForStatement, ast.WhileStatement), (ast.IfStatement,))
                  for row in context.nodes if isinstance(row.node, kinds)]
    for expression in conditions:
        inner = expression.operand if isinstance(expression, ast.UnaryExpression) and expression.operator == "!" else expression
        if (isinstance(inner, ast.BinaryExpression) and inner.operator in {"<", "<=", ">", ">="}
                and all(isinstance(part, (ast.Identifier, ast.Literal))
                        and context.semantic.expression_types[id(part)].display() == "int"
                        for part in (inner.left, inner.right))):
            start, end = inner.span.start.offset, inner.span.end.offset
            swap = f"({context.text(inner.right.span)} {REVERSE[inner.operator]} {context.text(inner.left.span)})"
            yield "reverse_comparison", source[:start]+swap+source[end:], "f"
            break


def probe_controls():
    from backend.app.routes.behavioral import wire
    from execution_service.contracts import Batch, BatchResult, LocalLimits, Program, TestVector

    examples = {
        "recursive_boundary": ("int f(int n){if(n<=2){return 0;}return 1+f(n-1);}",
                               "int f(int n){if(n<=3){return 0;}return 1+f(n-1);}"),
        "return_equivalence": ("int f(int x){int q=x;return q;}", "int f(int x){int q=x;return q+0;}"),
        "recursive_limit": ("int f(int n){if(n<=1){return 0;}return f(n);}",
                            "int f(int n){if(n<=1){return 0;}return f(n-1);}"),
    }
    data = {}
    for name, pair in examples.items():
        packet = Batch(engine_version=5, entry_point="f", limits=LocalLimits(), trace=False,
                       vectors=(TestVector(arguments=(1,), expected=0 if name != "return_equivalence" else 1),),
                       programs=(Program(source=pair[0]), *(Program(source=source, candidate_id=f"IR-{i:012x}")
                                                           for i, source in enumerate(pair, 1))))
        answer = wire(Path(os.environ["INTENTFORGE_VM_SOCKET"]), "/internal/verify", packet.model_dump_json().encode())
        assert answer["availability"]["status"] == "available"
        result = BatchResult.model_validate(answer["result"])
        data[name] = {"passing": sum(run.status == Status.MATCHES_SUPPLIED_TESTS for run in result.runs[1:]),
                      "pairs": sum(item.new_pairs for item in result.probes),
                      "steps": sum(item.steps for item in result.probes),
                      "distinguishing_inputs": [list(item.arguments) for item in result.probes if item.new_pairs],
                      "assessments": sorted({item.assessment for item in result.probes})}
    return data


def isolated(cases):
    from fastapi.testclient import TestClient
    from backend.app.main import app

    elapsed, results = [], []
    with TestClient(app, base_url="http://127.0.0.1:8000", client=("127.0.0.1", 40200)) as client:
        for _ in range(5):
            capability = client.get(URL + "/capability").json()
            if capability["status"] != "capacity_reached":
                break
            sleep(.25)
        assert capability["status"] == "available", capability
        for case in cases:
            payload = {"source": case["source"], "vectors": case["vectors"], "engine_version": 6,
                       "entry_point": "f", "compare_candidates": True}
            start = perf_counter()
            result = client.post(URL, json=payload).json()
            elapsed.append(1000*(perf_counter()-start))
            assert result["availability"]["status"] == "available" and result["requires_approval"], result
            candidates = {item["id"]: item for item in result["candidates"]}
            exact = {repair_key(source) for source in case["references"]}
            passing_other = sum(item["behavior"]["status"] == "MATCHES_SUPPLIED_TESTS" and repair_key(item["source"]) not in exact
                                for item in candidates.values()) if exact else 0
            reviewed = [candidates[key]["source"] for key in result["review_order"]]
            original = result["original"]
            answer = {
                "id": case["id"], "original": original["status"], "issue": (original["execution"]["issue"] or {}).get("code"),
                "candidate_statuses": [item["behavior"]["status"] for item in candidates.values()],
                "static_rank": rank(case, [item["source"] for item in candidates.values()]), "observed_rank": rank(case, reviewed),
                "other_candidates_matching_vectors": passing_other,
                "comparison": result["comparison_status"], "probes": len(result["probes"]),
                "separated_pairs": sum(item["new_pairs"] for item in result["probes"]),
                "probe_steps": sum(item["steps"] for item in result["probes"]),
                "test_steps": sum(sample["steps"] for run in [original, *(item["behavior"] for item in candidates.values())]
                                  for sample in run["execution"]["samples"]),
            }
            if case["disposition"] == "ambiguous":
                observed = client.post(URL, json={**payload, "vectors": []}).json()
                assert observed["availability"]["status"] == "available" and observed["comparison_status"] is None
                assert all("expected" not in item for item in observed["probes"])
                assert observed["review_order"] == [item["id"] for item in observed["candidates"]]
                answer["observation_only_pairs"] = sum(item["new_pairs"] for item in observed["probes"])
            results.append(answer)
    faults = [item for case, item in zip(cases, results, strict=True) if case["references"]]
    return {
        "cases": results, "controlled_probes": probe_controls(), "latency": latency(elapsed),
        "metrics": {key: {f"top{limit}": fraction(sum(item[key] is not None and item[key] <= limit
                                                     for item in faults), len(faults)) for limit in (1,3)}
                    for key in ("static_rank", "observed_rank")},
    }


def evaluate(live=False):
    cases, audit_report = audit()
    independent_references(cases)
    ranker, _ = load_generalized_ranker(4)
    assert ranker is not None
    cohorts = {key: [case for case in cases if case["partition"] == key]
               for key in ("development", "selection", "calibration", "final")}
    final = cohorts["final"]
    output = {"audit": audit_report}
    output.update((key, static(rows, ranker)) for key, rows in cohorts.items())
    output["robustness"] = robustness(final)
    output["provenance_groups"] = {}
    for provenance in ("external_adaptation", "internal"):
        selected = [(case, result) for case, result in zip(final, output["final"]["rows"]["phase6"], strict=True)
                    if case["provenance"]["group"] == provenance]
        output["provenance_groups"][provenance] = metrics([case for case, _ in selected], [row for _, row in selected])
    output["semantic_categories"] = dict(sorted(Counter(category for case in output["final"]["rows"]["phase6"]
                                                        for category in case["categories"] if category in CATEGORIES).items()))
    if live:
        output["live"] = isolated(final)
    return output


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--live", action="store_true")
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    result = evaluate(args.live)
    if args.check:
        observed = result.pop("live", None)
        assert stable(result) == stable(json.loads((REPORTS / "phase6-static-v1.json").read_text())), "Static replay changed"
        if args.live:
            assert stable(observed) == stable(json.loads((REPORTS / "phase6-live-v1.json").read_text())), "Isolated replay changed"
        print(f"Verified {len(result['final']['rows']['phase6'])} admitted Phase 6 final cases.")
    else:
        print(json.dumps(result, indent=2))
