"""Reproduce Phase 5.5 precision, transfer, same-pool ranking and isolated review."""
import argparse
from collections import Counter
from copy import copy
from difflib import SequenceMatcher
import json
import os
from pathlib import Path
from time import perf_counter

from ai.behavior_oracle import ExecutionLimits, Status, Vector
from ai.correction_safety import repair_key
from ai.intention_context import Requirement, build_context
from ai.intention_engine import analyze_intention, order_candidates
from ai.intention_phase5 import evidence_order
from ai.intention_phase55 import RULES
from ai.intention_v3_ranker import load_generalized_ranker
from benchmarks.phase5_evaluate import fraction, latency
from benchmarks.phase55_audit import audit
from compiler import ast_nodes as ast
from compiler.lexer import tokenize
from vm.behavioral_executor import MiniCOracle

REPORTS = Path(__file__).with_name("reports")
ALERT = {"COMPILER_ERROR", "HEURISTIC_SUSPICION", "SPECIFICATION_SUPPORTED_SUSPICION"}
URL = "/v1/behavioral-verification"


def vectors(case):
    return tuple(Vector(arguments=args, expected=expected)
                 for args, expected in zip(case["input_vectors"], case["expected_outputs"], strict=True))


def reference_rank(case, sources):
    references = {repair_key(text) for text in (*case["reference_repairs"], *case["acceptable_alternatives"])}
    return next((index for index, source in enumerate(sources, 1) if repair_key(source) in references), None)


def edit_locations(source, reference, candidate):
    old, _ = tokenize(source)
    new, _ = tokenize(reference)
    old_keys, new_keys = ([token.lexeme for token in tokens] for tokens in (old, new))
    changed = []
    for tag, left, right, _, _ in SequenceMatcher(None, old_keys, new_keys, autojunk=False).get_opcodes():
        if tag != "equal" and left < right:
            changed.extend(token.span.start.offset for token in old[left:right])
    return bool(changed) and all(any(edit.span.start.offset <= point < edit.span.end.offset for edit in candidate.proposal.edits)
                                 for point in changed)


def record(case, result, pool=None):
    items = result.candidates if pool is None else pool
    original = case["mini_c_source"]
    ids = {item.id for item in items}
    usable = [item for item in items if item.compiler_valid]
    located = sum(any(edit_locations(original, ref, item) for ref in case["reference_repairs"]) for item in usable)
    return {"case": case["case_id"], "alert": result.finding in ALERT, "rank": reference_rank(case, [item.proposed_code for item in items]),
            "candidates": len(items), "valid": len(usable), "attempts": result.attempts, "duplicate_ids": len(items)-len(ids),
            "candidate_edit_location_hits": located, "multi_edits": sum(len(item.proposal.edits) > 1 for item in items),
            "scored": sum(item.relative_score is not None for item in items),
            "recommendation": result.to_dict()["recommendation"], "unsupported": result.finding == "UNSUPPORTED_LANGUAGE",
            "findings": [item["category"] for item in (result.structural_scan or {}).get("findings", ())],
            "withheld": [{key: row[key] for key in ("category", "counter_evidence")}
                         for row in (result.structural_scan or {}).get("withheld", ())]}


def summarize(cases, records):
    faults = [(case, row) for case, row in zip(cases, records, strict=True) if case["reference_repairs"]]
    controls = [row for case, row in zip(cases, records, strict=True) if case["is_known_correct"]]
    found = sum(row["alert"] for _, row in faults)
    false = sum(row["alert"] for row in controls)
    recommendations = [row for row in records if row["recommendation"] == "REVIEW_WITH_EVIDENCE"]
    metrics = {"recall": fraction(found, len(faults)), "precision": fraction(found, found+false),
               "false_positive_rate": fraction(false, len(controls)), "false_negative_rate": fraction(len(faults)-found, len(faults)),
               "candidate_recall": fraction(sum(row["rank"] is not None for _, row in faults), len(faults)),
               "top1": fraction(sum(row["rank"] == 1 for _, row in faults), len(faults)),
               "top3": fraction(sum(row["rank"] is not None and row["rank"] <= 3 for _, row in faults), len(faults)),
               "location_recall": fraction(sum(bool(row["candidate_edit_location_hits"]) for _, row in faults), len(faults)),
               "compiler_validity": fraction(sum(row["valid"] for row in records), sum(row["candidates"] for row in records)),
               "recommendation_coverage": fraction(len(recommendations), len(records)),
               "incorrect_or_unconfirmed_recommendations": fraction(sum(row["rank"] != 1 for row in recommendations), len(recommendations)),
               "per_category": {}, "attempts": sum(row["attempts"] for row in records),
               "duplicate_ids": sum(row["duplicate_ids"] for row in records), "multi_edits": sum(row["multi_edits"] for row in records),
               "unsupported": sum(row["unsupported"] for row in records), "learned_scored": sum(row["scored"] for row in records)}
    for category in sorted({case["fault_category"] for case, _ in faults}):
        subset = [row for case, row in faults if case["fault_category"] == category]
        metrics["per_category"][category] = {"detection": fraction(sum(row["alert"] for row in subset), len(subset)),
                                            "generation": fraction(sum(row["rank"] is not None for row in subset), len(subset))}
    return metrics


def strategies(cases, ranker, *, individual=False):
    configurations = {key: [] for key in
        ("phase5", "phase55", "same_pool_evidence_order", "same_pool_v4", "same_pool_pairwise")}
    if individual:
        configurations.update({rule: [] for rule in sorted(RULES)})
    timing = []
    for case in cases:
        source = case["mini_c_source"]
        baseline = analyze_intention(source, phase5=True)
        started = perf_counter()
        selected = analyze_intention(source, phase55=True)
        timing.append((perf_counter()-started)*1000)
        assert selected.context.compiler_valid == (case["program_validity"] == "compiler_valid"), case["case_id"]
        configurations["phase5"].append(record(case, baseline))
        configurations["phase55"].append(record(case, selected))
        configurations["same_pool_evidence_order"].append(record(case, selected, evidence_order(selected.candidates)))
        for key, method in (("same_pool_v4", None), ("same_pool_pairwise", "pairwise")):
            pool = order_candidates([copy(item) for item in selected.candidates], None, expanded=ranker,
                                    generalized=True, experimental=method)
            assert {item.id for item in pool} == {item.id for item in selected.candidates}
            configurations[key].append(record(case, selected, pool))
        if individual:
            for rule in sorted(RULES):
                result = analyze_intention(source, phase55=True, phase55_rules=frozenset({rule}))
                configurations[rule].append(record(case, result))
    return {"metrics": {key: summarize(cases, items) for key, items in configurations.items()},
            "rows": configurations, "latency": latency(timing)}


def check_references(cases):
    oracle = MiniCOracle()
    for case in cases:
        if case["is_ambiguous"]:
            continue
        source = case["mini_c_source"]
        for reference in case["reference_repairs"] or [source]:
            assert oracle.verify(reference, "f", vectors(case), ExecutionLimits()).status == Status.MATCHES_SUPPLIED_TESTS, case["case_id"]
        if case["reference_repairs"]:
            assert oracle.verify(source, "f", vectors(case), ExecutionLimits()).status != Status.MATCHES_SUPPLIED_TESTS, case["case_id"]


def transformed(source):
    tokens = tokenize(source)[0]
    names = {token.lexeme: f"metamorph_{i}" for i, token in enumerate(tokens) if token.type == "IDENTIFIER"}
    yield "alpha_rename", " ".join(names.get(t.lexeme, t.lexeme) if t.type == "IDENTIFIER" else t.lexeme for t in tokens), names["f"]
    yield "format", "\n".join(token.lexeme for token in tokens), "f"
    context = build_context(source)
    returned = next((row.node.value for row in context.nodes
                     if isinstance(row.node, ast.ReturnStatement) and row.node.value), None)
    if returned:
        start, end = returned.span.start.offset, returned.span.end.offset
        yield "parenthesize_return", source[:start] + "(" + source[start:end] + ")" + source[end:], "f"
    flip = {"<": ">", "<=": ">=", ">": "<", ">=": "<="}
    loop_conditions = [row.node.condition for row in context.nodes if isinstance(row.node, (ast.ForStatement, ast.WhileStatement))]
    condition = next((expression for expression in [*loop_conditions, *(row.node for row in context.nodes)]
                      if isinstance(expression, ast.BinaryExpression) and expression.operator in flip
                      and all(isinstance(node, (ast.Identifier, ast.Literal))
                              for node in (expression.left, expression.right))), None)
    if condition:
        start, end = condition.span.start.offset, condition.span.end.offset
        yield "reverse_comparison", (source[:start] + context.text(condition.right.span) + flip[condition.operator]
                                     + context.text(condition.left.span) + source[end:]), "f"
    for row in context.nodes:
        if not isinstance(row.node, ast.Block):
            continue
        for left, right in zip(row.node.statements, row.node.statements[1:]):
            if (isinstance(left, ast.VariableDeclaration) and isinstance(right, ast.VariableDeclaration)
                    and isinstance(left.initializer, ast.Literal) and isinstance(right.initializer, ast.Literal)):
                a, b = left.span.start.offset, left.span.end.offset
                c, d = right.span.start.offset, right.span.end.offset
                yield "swap_independent_initializers", source[:a] + source[c:d] + source[b:c] + source[a:b] + source[d:], "f"
                return


def robustness(cases):
    oracle = MiniCOracle()
    outcomes = []
    for case in cases:
        if case["is_ambiguous"]:
            continue
        source = case["mini_c_source"]
        base = analyze_intention(source, phase55=True)
        observed = oracle.verify(source, "f", vectors(case), ExecutionLimits())
        for mode, code, entry in transformed(source):
            result = analyze_intention(code, phase55=True)
            rerun = oracle.verify(code, entry, vectors(case), ExecutionLimits())
            equivalent = (rerun.status == observed.status and
                          [row.actual for row in rerun.observations] == [row.actual for row in observed.observations])
            assert equivalent and result.context.compiler_valid == base.context.compiler_valid, (case["case_id"], mode)
            assert all(0 <= edit.span.start.offset <= edit.span.end.offset <= len(code)
                       for item in result.candidates for edit in item.proposal.edits)
            common = {tuple(item.proposal.category for item in run.candidates) for run in (base, result)}
            outcomes.append({"case": case["case_id"], "family": case["source_family"], "transformation": mode,
                             "behavior_equivalent": equivalent, "alert_consistent": (result.finding in ALERT) == (base.finding in ALERT),
                             "candidate_categories_consistent": len(common) == 1})
    return outcomes


def guided(cases, mode):
    cohort = [case for case in cases if case["reference_repairs"] and (mode == "natural" or case.get("guidance"))]
    records = []
    for case in cohort:
        requirements = {"description": case["specification"]} if mode == "natural" else case["guidance"]
        result = analyze_intention(case["mini_c_source"], Requirement(function="f", **requirements), phase55=True)
        records.append(record(case, result))
    return {"metrics": summarize(cohort, records), "rows": records}


def live(cases):
    from fastapi.testclient import TestClient
    from backend.app.main import app
    from backend.app.routes.behavioral import wire
    from execution_service.contracts import Batch, BatchResult, LocalLimits, Program, TestVector

    records = []
    timing = []
    with TestClient(app, base_url="http://127.0.0.1:8000", client=("127.0.0.1", 49000)) as client:
        assert client.get(URL + "/capability").json()["status"] == "available"
        for case in cases:
            payload = {"source": case["mini_c_source"], "entry_point": "f", "engine_version": 55, "compare_candidates": True,
                       "vectors": [item.model_dump(mode="json") for item in vectors(case)]}
            started = perf_counter()
            result = client.post(URL, json=payload).json()
            timing.append((perf_counter()-started)*1000)
            assert result["availability"]["status"] == "available" and result["requires_approval"], result
            pool = {item["id"]: item for item in result["candidates"]}
            probes = result["probes"]
            row = {"case": case["case_id"], "static_rank": reference_rank(case, [item["source"] for item in pool.values()]),
                   "observed_rank": reference_rank(case, [pool[key]["source"] for key in result["review_order"]]),
                   "original": result["original"]["status"], "candidate_statuses": [item["behavior"]["status"] for item in pool.values()],
                   "comparison": result["comparison_status"], "probes": len(probes),
                   "redundant_probes": sum(item["new_pairs"] == 0 for item in probes),
                   "distinct_pairs": sum(item["new_pairs"] for item in probes),
                   "probe_steps": sum(item["steps"] for item in probes)}
            if case["is_ambiguous"]:
                observation = client.post(URL, json={**payload, "vectors": []}).json()
                assert observation["availability"]["status"] == "available" and observation["comparison_status"] is None
                assert observation["review_order"] == [item["id"] for item in observation["candidates"]]
                assert all("expected" not in probe for probe in observation["probes"])
                row["observation_only_pairs"] = sum(probe["new_pairs"] for probe in observation["probes"])
            records.append(row)
    # Known benchmark alternatives enter only through the private trusted fixture transport.
    fixtures = {
        "equivalent_add_zero": ("int f(int x){return x;}", "int f(int x){return x+0;}"),
        "boundary_fault": ("int f(int x){return x;}", "int f(int x){if(x==15){return x/(x-x);}return x;}"),
        "partial_first_reading": ("int f(int x){return x;}", "int f(int x){return 4;}"),
    }
    controlled = {}
    for label, pair in fixtures.items():
        batch = Batch(entry_point="f", engine_version=5, limits=LocalLimits(), trace=False,
                      vectors=(TestVector(arguments=(4,), expected=4),),
                      programs=(Program(source=pair[0]), *(Program(source=source, candidate_id=f"IR-{i:012x}")
                                                          for i, source in enumerate(pair, 1))))
        reply = wire(Path(os.environ["INTENTFORGE_VM_SOCKET"]), "/internal/verify", batch.model_dump_json().encode())
        assert reply["availability"]["status"] == "available", reply
        result = BatchResult.model_validate(reply["result"])
        controlled[label] = {"passing": sum(run.status == Status.MATCHES_SUPPLIED_TESTS for run in result.runs[1:]),
                             "pairs": sum(row.new_pairs for row in result.probes),
                             "runtime_probe": any(row.assessment == "candidate_runtime_failure" for row in result.probes),
                             "probe_steps": sum(row.steps for row in result.probes)}
    return {"cases": records, "controlled": controlled, "latency": latency(timing)}


def evaluate(run_live):
    cases, audited = audit()
    check_references(cases)
    ranker, _ = load_generalized_ranker(4)
    assert ranker is not None
    split = lambda name: [case for case in cases if case["partition"] == name]
    development = strategies(split("development"), ranker, individual=True)
    selection = strategies(split("selection"), ranker)
    final = split("final")
    selected = strategies(final, ranker)
    groups = {}
    for group in ("external_adaptation", "internal"):
        logical = [(case, row) for case, row in zip(final, selected["rows"]["phase55"], strict=True) if case["origin_group"] == group]
        groups[group] = summarize([case for case, _ in logical], [row for _, row in logical])
    familiar = {case["fault_category"] for case in cases if case["partition"] != "final" and case["reference_repairs"]}
    transfer = {}
    for label, known in (("familiar_category", True), ("new_category", False)):
        logical = [(case, row) for case, row in zip(final, selected["rows"]["phase55"], strict=True)
                   if case["reference_repairs"] and (case["fault_category"] in familiar) == known]
        transfer[label] = summarize([case for case, _ in logical], [row for _, row in logical])
    report = {"audit": audited, "development": development, "selection": selection, "final": selected,
              "origin_groups": groups, "transfer": transfer, "robustness": robustness(final),
              "natural": guided(final, "natural"), "explicit": guided(final, "explicit")}
    if run_live:
        report["live"] = live(final)
    return report


def stable(value):
    if isinstance(value, dict):
        return {key: stable(item) for key, item in value.items() if key != "latency"}
    if isinstance(value, list):
        return [stable(item) for item in value]
    return value


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--live", action="store_true")
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    report = evaluate(args.live)
    if args.check:
        live_report = report.pop("live", None)
        assert stable(report) == stable(json.loads((REPORTS / "phase55-static-v1.json").read_text()))
        if args.live:
            assert stable(live_report) == stable(json.loads((REPORTS / "phase55-live-v1.json").read_text()))
        print(f"Verified {len(report['final']['rows']['phase55'])} admitted Phase 5.5 final cases.")
    else:
        print(json.dumps(report, indent=2))
