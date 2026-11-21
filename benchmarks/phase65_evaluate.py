"""Replay independent Phase 6.5 ablations and restricted worker observations."""
import argparse
from collections import Counter
from copy import copy
import json
import os
from pathlib import Path
from time import perf_counter, sleep

from ai.behavior_oracle import ExecutionLimits, Status
from ai.intention_context import Example, build_context
from ai.intention_engine import analyze_intention, order_candidates
from ai.intention_v3_ranker import load_generalized_ranker
from compiler import ast_nodes as ast
from vm.behavioral_executor import MiniCOracle

from .phase5_evaluate import fraction, latency
from .phase55_evaluate import stable
from .phase6_evaluate import ALERTS, REPORTS, URL, independent_references, metrics, rank, row, safe_transforms, vectors
from .phase65_audit import audit

CONFIGURATIONS = {
    "phase5": {"phase5": True},
    "phase55": {"phase55": True},
    "phase6": {"phase6": True},
    "paths_only": {"phase65_components": frozenset()},
    "recursion_only": {"phase65_components": frozenset({"recursion"})},
    "precision_only": {"phase65_components": frozenset({"precision"})},
    "recurrence_guided": {"phase65_components": frozenset({"recurrence"}), "guided": True},
    "combined": {},
    "combined_guided": {"guided": True},
}


def analyze(case, **settings):
    guided = settings.pop("guided", False)
    prior = {"phase5", "phase55", "phase6"} & settings.keys()
    examples = tuple(Example(tuple(v.arguments), v.expected) for v in vectors(case)) if guided else ()
    return analyze_intention(case["source"], phase65=not prior, phase6_entry="f", phase6_examples=examples, **settings)


def score(cases, ranker):
    rows = {key: [] for key in (*CONFIGURATIONS, "v4_same_pool", "pairwise_same_pool",
                                "v4_guided_same_pool", "pairwise_guided_same_pool")}
    timings = []
    for case in cases:
        for name, settings in CONFIGURATIONS.items():
            start = perf_counter()
            analysis = analyze(case, **settings)
            if name == "combined":
                timings.append(1000*(perf_counter()-start))
            assert analysis.context.compiler_valid and all(item.compiler_valid for item in analysis.candidates)
            value = row(case, analysis, analysis.candidates)
            extended = (analysis.program_analysis or {}).get("phase65", {})
            value["withheld"] = [item["category"] for item in extended.get("withheld", [])]
            value["provenance"] = [item.get("hypothesis_origin") for item in analysis.to_dict()["candidates"]]
            rows[name].append(value)
            if name in {"combined", "combined_guided"}:
                label = "_guided" if name == "combined_guided" else ""
                for key, mode in [(f"v4{label}_same_pool", None), (f"pairwise{label}_same_pool", "pairwise")]:
                    reordered = order_candidates([copy(item) for item in analysis.candidates], None, expanded=ranker,
                                                 generalized=True, experimental=mode)
                    assert {item.id for item in reordered} == {item.id for item in analysis.candidates}
                    rows[key].append(row(case, analysis, reordered))
    output = {name: metrics(cases, values) | {
        "recommendation_coverage": fraction(sum(r["recommendation"] == "REVIEW_WITH_EVIDENCE" for r in values), len(values)),
        "multiple_candidates": fraction(sum(r["candidates"] > 1 for r in values), len(values)),
    } for name, values in rows.items()}
    return {"rows": rows, "metrics": output, **({"latency": latency(timings)} if timings else {})}


def transform_paths(source):
    yield from safe_transforms(source)
    context = build_context(source)
    for record in context.nodes:
        node = record.node
        if isinstance(node, ast.IfStatement) and node.else_branch is None and isinstance(node.then_branch, ast.Block):
            function = record.function
            statements = function.body.statements
            if len(statements) == 2 and statements[0] is node and isinstance(statements[1], ast.ReturnStatement):
                condition = context.text(node.condition.span)
                left, right = node.then_branch, statements[1]
                text = f"if(!({condition})){{{context.text(right.span)}}}return {context.text(left.statements[0].value.span)};"
                yield "reverse_guard_and_returns", source[:node.span.start.offset]+text+source[right.span.end.offset:], "f"
                break
    for record in context.nodes:
        node = record.node
        if isinstance(node, ast.ReturnStatement) and node.value is not None:
            start, end = node.value.span.start.offset, node.value.span.end.offset
            yield "parenthesize_return", source[:start]+"("+source[start:end]+")"+source[end:], "f"
            yield "unused_shadow_scope", source[:node.span.start.offset]+"{int phaseprobe=1;{int phaseprobe=2;}}"+source[node.span.start.offset:], "f"
            break


def robustness(cases):
    oracle = MiniCOracle()
    output = []
    for case in cases:
        if case["disposition"] == "ambiguous":
            continue
        original = oracle.verify(case["source"], "f", vectors(case), ExecutionLimits())
        base = analyze(case)
        before = sorted(item.proposal.category for item in base.candidates)
        for name, transformed, entry in transform_paths(case["source"]):
            result = oracle.verify(transformed, entry, vectors(case), ExecutionLimits())
            assert result.status == original.status and [r.actual for r in result.observations] == [
                r.actual for r in original.observations], (case["id"], name, result.status)
            current = analyze_intention(transformed, phase65=True, phase6_entry=entry)
            assert current.context.compiler_valid and all(item.compiler_valid for item in current.candidates)
            output.append({"id": case["id"], "transform": name,
                           "alert_preserved": (current.finding in ALERTS) == (base.finding in ALERTS),
                           "categories_preserved": sorted(item.proposal.category for item in current.candidates) == before})
    return output


def controlled_probes():
    from backend.app.routes.behavioral import wire, validate_identity
    from execution_service.contracts import Batch, BatchResult, LocalLimits, Program, TestVector

    examples = {
        "multi_argument_threshold": (("int f(int n,int a){if(n<=2){return a;}return f(n-1,a+1);}",
                                      "int f(int n,int a){if(n<=3){return a;}return f(n-1,a+1);}"), (2,7), 7),
        "recurrence_operator": (("int f(int n){if(n<=1){return n;}return f(n-1)+f(n-2);}",
                                 "int f(int n){if(n<=1){return n;}return f(n-1)-f(n-2);}"), (2,), 1),
        "return_path": (("int f(int n,int m){if(m<=2){return n+2;}return n*3;}",
                         "int f(int n,int m){if(m<=2){return n+2;}return n*4;}"), (3,2), 5),
        "equivalent_return": (("int f(int n){if(n<=2){return n;}return 2;}",
                               "int f(int n){if(n<=2){return n+0;}return 2;}"), (1,), 1),
    }
    data = {}
    for name, (pair, arguments, expected) in examples.items():
        programs = (Program(source=pair[0]), *(Program(source=source, candidate_id=f"IR-{i:012x}")
                                                  for i, source in enumerate(pair, 1)))
        batch = Batch(engine_version=5, entry_point="f", limits=LocalLimits(), trace=False, programs=programs,
                      vectors=(TestVector(arguments=arguments, expected=expected),))
        answer = wire(Path(os.environ["INTENTFORGE_VM_SOCKET"]), "/internal/verify", batch.model_dump_json().encode())
        assert answer["availability"]["status"] == "available"
        result = BatchResult.model_validate(answer["result"])
        validate_identity(batch, result)
        data[name] = {"passing": sum(run.status == Status.MATCHES_SUPPLIED_TESTS for run in result.runs[1:]),
                      "pairs": sum(item.new_pairs for item in result.probes), "steps": sum(item.steps for item in result.probes),
                      "distinguishing_inputs": [list(item.arguments) for item in result.probes if item.new_pairs]}
    return data


def live(cases):
    from fastapi.testclient import TestClient
    from backend.app.main import app

    outcomes, timings = [], []
    with TestClient(app, base_url="http://127.0.0.1:8000", client=("127.0.0.1", 40200)) as client:
        for _ in range(5):
            capability = client.get(URL+"/capability").json()
            if capability["status"] != "capacity_reached":
                break
            sleep(.25)
        assert capability["status"] == "available", capability
        for case in cases:
            request = dict(source=case["source"], vectors=case["vectors"], engine_version=65, entry_point="f", compare_candidates=True)
            start = perf_counter()
            reply = client.post(URL, json=request)
            timings.append(1000*(perf_counter()-start))
            assert reply.status_code == 200, reply.text
            answer = reply.json()
            assert answer["availability"]["status"] == "available" and answer["requires_approval"], answer
            candidates = {item["id"]: item for item in answer["candidates"]}
            static = analyze(case, guided=True)
            assert list(candidates) == [choice.id for choice in static.candidates[:4]]
            review = answer["review_order"]
            assert set(review) == set(candidates)
            statuses = {key: item["behavior"]["status"] for key, item in candidates.items()}
            passing = [key for key, status in statuses.items() if status == Status.MATCHES_SUPPLIED_TESTS]
            runs = [answer["original"], *(item["behavior"] for item in candidates.values())]
            execution = runs[0]["execution"]
            assert execution
            steps = sum(sample["steps"] for item in runs if item["execution"] for sample in item["execution"]["samples"])
            probe_steps = sum(item["steps"] for item in answer["probes"])
            assert steps+probe_steps <= 200000
            outcome = {
                "id": case["id"], "original": answer["original"]["status"], "issue": (execution["issue"] or {}).get("code"),
                "candidate_statuses": list(statuses.values()), "static_rank": rank(case, [item["source"] for item in candidates.values()]),
                "behavioral_rank": rank(case, [candidates[key]["source"] for key in review]),
                "passing_candidates": len(passing), "passing_exact": bool(rank(case,[candidates[key]["source"] for key in passing])),
                "comparison": answer["comparison_status"], "test_steps": steps, "probe_steps": probe_steps,
                "probes": len(answer["probes"]), "separated_pairs": sum(item["new_pairs"] for item in answer["probes"]),
            }
            if case["disposition"] == "ambiguous":
                observed = client.post(URL, json=request | {"vectors": []}).json()
                assert observed["comparison_status"] is None
                assert all("expected" not in item for item in observed["probes"])
            outcomes.append(outcome)
    faults = [outcome for case, outcome in zip(cases, outcomes, strict=True) if case["references"]]
    return {"cases": outcomes, "controlled_probes": controlled_probes(), "latency": latency(timings), "metrics": {
        "test_agreeing_repair": fraction(sum(r["passing_candidates"] > 0 for r in faults), len(faults)),
        "exact_and_test_agreeing": fraction(sum(r["passing_exact"] for r in faults), len(faults)),
        **{key: {f"top{n}": fraction(sum(r[key] is not None and r[key] <= n for r in faults), len(faults))
                 for n in (1,3)} for key in ("static_rank", "behavioral_rank")},
        "execution_supported": fraction(len(outcomes), len(cases)),
        "original_statuses": dict(Counter(r["original"] for r in outcomes)),
        **{key: sum(r[key] for r in outcomes) for key in ("test_steps", "probe_steps", "probes", "separated_pairs")},
    }}


def evaluate(use_worker):
    cases, audit_report = audit()
    independent_references(cases)
    ranker, _ = load_generalized_ranker(4)
    assert ranker is not None
    partitions = {key: [r for r in cases if r["partition"] == key] for key in ("development","selection","calibration","final")}
    final = partitions["final"]
    output = {name: score(rows, ranker) for name, rows in partitions.items()}
    output["audit"] = audit_report
    output["robustness"] = robustness(final)
    output["final_provenance"] = {}
    for origin in ("external_adaptation", "authored"):
        output["final_provenance"][origin] = {}
        for engine in ("phase6", "combined", "combined_guided"):
            subset = [(case, result) for case, result in zip(final, output["final"]["rows"][engine], strict=True)
                      if case["provenance"]["group"] == origin]
            output["final_provenance"][origin][engine] = metrics([case for case, _ in subset], [result for _, result in subset])
    return output, live(final) if use_worker else None


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--live", action="store_true")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--check", action="store_true")
    mode.add_argument("--write", action="store_true")
    args = parser.parse_args()
    static, observed = evaluate(args.live)
    reports = {"static": static, "audit": static["audit"]}
    if args.live:
        reports["live"] = observed
    for name, report in reports.items():
        path = REPORTS/f"phase65-{name}-v1.json"
        if args.check:
            assert stable(report) == stable(json.loads(path.read_text())), f"Phase 6.5 {name} replay changed"
        elif args.write:
            path.write_text(json.dumps(report, indent=2)+"\n")
    if args.check or args.write:
        print(f"Phase 6.5: {len(static['final']['rows']['combined'])} admitted final cases")
    else:
        print(json.dumps(reports, indent=2))
