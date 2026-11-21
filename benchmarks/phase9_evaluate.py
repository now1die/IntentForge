"""Replay Phase 9 ablations, transformations and independent worker holdout."""
import argparse
from collections import Counter
import json
from time import monotonic, perf_counter, sleep

from ai.behavior_oracle import ExecutionLimits, Status, Vector
from ai.intention_context import build_context
from ai.intention_phase9 import CATEGORIES
from analysis_evidence.function_summary import analyze_program
from compiler import ast_nodes as ast
from vm.behavioral_executor import MiniCOracle

from .phase5_evaluate import fraction, latency
from .phase6_evaluate import REPORTS, URL, vectors
from .phase65_evaluate import transform_paths
from .phase7_evaluate import static
from .phase75_fixtures import ROOT as PHASE75_ROOT
from .phase85_evaluate import measured_case, observed, run_projection, summarize
from .phase85_fixtures import ROOT as PHASE85_ROOT
from .phase8_evaluate import worker_call
from .phase9_audit import audit

STAGES = {
    "phase65":{"phase65":True},
    "phase75":{"phase75":True},
    "phase85":{"phase85":True},
    "normalization":{"phase9":True,"phase9_components":frozenset({"normalization"})},
    "variable_steps":{"phase9":True,"phase9_components":frozenset({"normalization","variable_steps"})},
    "mixed_updates":{"phase9":True,"phase9_components":frozenset({"normalization","mixed_updates"})},
    "runtime":{"phase9":True,"phase9_components":frozenset({"runtime"})},
    "cross_branch":{"phase9":True,"phase9_components":frozenset({"cross_branch"})},
    "phase9":{"phase9":True},
}
ARCHIVED_FAILURES = {"third-slot-count-fault", "descending-window-credit-fault"}
ARCHIVED_TRANSFORMS = {"reverse_comparison", "unused_shadow_scope"}


def interpreter_suite(oracle, source, entry, expected):
    return oracle.verify(source, entry, expected, ExecutionLimits())


def reference_checks(oracle, cases):
    originals = {}
    for case in cases:
        examples = vectors(case)
        whole = tuple(Vector.model_validate(row) for row in case["holdout_vectors"])
        for code in case["references"] or [case["source"]]:
            for suite in (examples, whole) if whole else (examples,):
                assert interpreter_suite(oracle,code,"f",suite).status == Status.MATCHES_SUPPLIED_TESTS, case["id"]
        if case["disposition"] == "fault":
            result = interpreter_suite(oracle,case["source"],"f",examples)
            assert result.status in {Status.MISMATCHES_SUPPLIED_TESTS,Status.BEHAVIOR_UNKNOWN,Status.EXECUTION_LIMITED}, case["id"]
            originals[case["id"]] = {"status":result.status,"issue":result.execution.issue.code if result.execution.issue else None}
    return originals


def graph_evidence(source, entry):
    context = build_context(source)
    program = analyze_program(context, monotonic()+1)
    item = next(row for row in program.functions if row.function.name==entry)
    flow = item.flow
    return {
        "top_level_statements":[type(node).__name__ for node in item.function.body.statements],
        "ast":ast.pretty_ast(item.function),
        "loop_guards":[context.text(block.expression.span) for block in flow.graph.blocks
                       if block.kind=="loop_header"],
        "bindings":[{"id":key,"name":symbol.name,"span":symbol.declaration_span.to_dict()}
                    for key,symbol in sorted(program.bindings.symbols.items())],
        "cfg":flow.graph.to_dict(),
        "reaching":[{"site":i,"definitions":[{"site":row.site,"binding":row.binding} for row in sorted(incoming)]}
                    for i,incoming in enumerate(flow.incoming) if flow.graph.blocks[i].kind in {"loop_header","return"}],
    }


def archived(oracle):
    results = []
    data = json.loads((PHASE85_ROOT/"cases-v1.json").read_text())
    for case in data:
        if case["id"] not in ARCHIVED_FAILURES:
            continue
        samples = vectors(case)
        baseline = run_projection(case,phase85=True)
        original = interpreter_suite(oracle,case["source"],"f",samples)
        current = run_projection(case,phase9=True)
        for name,source,entry in transform_paths(case["source"]):
            if name not in ARCHIVED_TRANSFORMS:
                continue
            assert observed(interpreter_suite(oracle,source,entry,samples)) == observed(original)
            old = run_projection(case,source=source,entry=entry,phase85=True)
            new = run_projection(case,source=source,entry=entry,phase9=True)
            statuses = [interpreter_suite(oracle,c.proposed_code,entry,samples).status for c in new.candidates]
            assert old.program_analysis["phase85"]["status"] == "UNSUPPORTED_PROJECTION"
            assert baseline.candidates and statuses and all(status==Status.MATCHES_SUPPLIED_TESTS for status in statuses)
            assert [c.proposal.category for c in new.candidates] == [c.proposal.category for c in current.candidates]
            results.append({
                "id":case["id"],"transform":name,
                "root_cause":"left-only induction operand check" if name=="reverse_comparison" else "three top-level statement check",
                "original":{"source":case["source"],"evidence":graph_evidence(case["source"],"f")},
                "transformed":{"source":source,"evidence":graph_evidence(source,entry)},
                "phase85_original":[c.proposal.category for c in baseline.candidates],
                "phase85_transformed":[c.proposal.category for c in old.candidates],
                "phase9_transformed":[c.proposal.category for c in new.candidates],
                "identical_observed_behavior":True,"phase9_candidate_behavior":statuses,
                "requires_manual_approval":all(c["requires_approval"] for c in new.to_dict()["candidates"]),
            })
    assert len(results)==4
    return results


def rewrites(source):
    yield from transform_paths(source)
    context = build_context(source)
    for rec in context.nodes:
        node = rec.node
        if isinstance(node,ast.ForStatement) and isinstance(node.update,ast.UpdateExpression):
            operand = node.update.operand
            if isinstance(operand,ast.Identifier):
                lower, upper = node.update.span.start.offset, node.update.span.end.offset
                operator = "+" if node.update.operator=="++" else "-"
                yield "equivalent_latch", source[:lower]+f"{operand.name}={operand.name}{operator}1"+source[upper:], "f"
                break
    for function in context.parsed.ast.functions:
        first = function.body.statements[:2]
        parameters = {param.name for param in function.parameters}
        if len(first)==2 and all(isinstance(node,ast.VariableDeclaration) and
                                (isinstance(node.initializer,ast.Literal) or
                                 isinstance(node.initializer,ast.Identifier) and node.initializer.name in parameters)
                                for node in first) and first[0].name not in parameters:
            a,b = first
            chunks = source[a.span.end.offset:b.span.start.offset]
            yield "independent_declarations", (source[:a.span.start.offset]+context.text(b.span)+chunks+
                                               context.text(a.span)+source[b.span.end.offset:]), "f"
            break


def candidate_signature(oracle, candidates, entry, suite):
    return Counter((candidate.proposal.category, observed(interpreter_suite(oracle,candidate.proposed_code,entry,suite)))
                   for candidate in candidates)


def records(oracle,cases):
    candidates, transformations, differences, counters, timings = [], Counter(), [], Counter(), []
    effect_differences = []
    for case in cases:
        suite = vectors(case)
        start = perf_counter()
        original = run_projection(case,phase9=True)
        timings.append(1000*(perf_counter()-start))
        before = interpreter_suite(oracle,case["source"],"f",suite)
        report = original.program_analysis["phase9"]
        generated = [c for c in original.candidates if c.proposal.category in CATEGORIES]
        for choice in generated:
            assert choice.compiler_valid
            status = interpreter_suite(oracle,choice.proposed_code,"f",suite).status
            assert status == Status.MATCHES_SUPPLIED_TESTS, (case["id"],choice.proposed_code,status)
            counters[choice.proposal.category] += 1
        candidates.append({"id":case["id"],"component":report.get("mode"),"status":report["status"],
                           "single_trials":report["single_trials"],"pair_trials":report["pair_trials"],
                           "generated":len(generated)})
        base = sorted(c.proposal.category for c in original.candidates)
        original_effects = candidate_signature(oracle,original.candidates,"f",suite)
        for mode,source,entry in rewrites(case["source"]):
            changed = interpreter_suite(oracle,source,entry,suite)
            assert observed(before)==observed(changed), (case["id"],mode)
            result = run_projection(case,source=source,entry=entry,phase9=True)
            transformations[mode] += 1
            altered = sorted(c.proposal.category for c in result.candidates)
            if altered != base:
                differences.append({"id":case["id"],"transform":mode,"original":base,"transformed":altered})
            if candidate_signature(oracle,result.candidates,entry,suite) != original_effects:
                effect_differences.append({"id":case["id"],"transform":mode})
            for choice in result.to_dict()["candidates"]:
                assert choice["compiler_valid"] and choice["requires_approval"]
                for edit in choice["edits"]:
                    low,high=(edit["span"][position]["offset"] for position in ("start","end"))
                    assert edit["original"]==source[low:high]
    return {"candidates":candidates,"new_categories":dict(counters),"guided_latency":latency(timings),
            "metamorphic":{"count":sum(transformations.values()),"types":dict(transformations),"changed":differences,
                           "changed_candidate_effects":effect_differences}}


def provenance_metrics(cases,runs):
    summaries = {}
    for name,selected in {
        "adapted_real_defect":[i for i,c in enumerate(cases) if c["fault_origin"]=="adapted-real-defect"],
        "project_injected":[i for i,c in enumerate(cases) if c["fault_origin"]=="project-injected"],
        "correct_control":[i for i,c in enumerate(cases) if c["disposition"]=="control"],
        "incomplete_specification":[i for i,c in enumerate(cases) if c["disposition"]=="ambiguous"],
        "runtime_fault":[i for i,c in enumerate(cases) if c["disposition"]=="fault" and
                         runs[i]["policy"]["original"]=="RUNTIME_FAILURE"],
    }.items():
        subset = [runs[i] for i in selected]
        summaries[name] = {
            "count":len(subset),
            "confirmed_mismatch":fraction(sum(run["policy"]["confirmed_fault"] for run in subset),len(subset)),
            "has_candidate":fraction(sum(bool(run["candidate_ids"]) for run in subset),len(subset)),
            "acceptable_repair":fraction(sum(any(hit["status"]==Status.MATCHES_SUPPLIED_TESTS for hit in run["holdout"])
                                             for run in subset),len(subset)),
            "exact_repair":fraction(sum(any(hit["exact"] and hit["status"]==Status.MATCHES_SUPPLIED_TESTS
                                            for hit in run["holdout"]) for run in subset),len(subset)),
        }
    return summaries


def isolated(cases):
    from fastapi.testclient import TestClient
    from backend.app.main import app

    runs, timings = {str(v):[] for v in (75,85,9)}, {str(v):[] for v in (75,85,9)}
    observation_only = []
    with TestClient(app,base_url="http://127.0.0.1:8000",client=("127.0.0.1",41909)) as client:
        for _ in range(5):
            capability = client.get(URL+"/capability").json()
            if capability["status"] != "capacity_reached":
                break
            sleep(.25)
        assert capability["status"]=="available", capability
        for case in cases:
            for version in runs:
                start = perf_counter()
                runs[version].append(measured_case(client,case,int(version)))
                timings[version].append(1000*(perf_counter()-start))
            if case["disposition"]=="ambiguous":
                evidence = worker_call(client,dict(source=case["source"],engine_version=9,entry_point="f",
                                                   vectors=[],compare_candidates=True))
                assert evidence["guided_evidence"]["original"]=="INSUFFICIENT_SPECIFICATION"
                assert all("expected" not in probe for probe in evidence["probes"])
                observation_only.append({"id":case["id"],"probes":len(evidence["probes"])})
    return {
        "profiles":runs,"metrics":{version:summarize(cases,rows) for version,rows in runs.items()},
        "by_provenance":{version:provenance_metrics(cases,rows) for version,rows in runs.items()},
        "latency":{version:latency(times) for version,times in timings.items()},"observation_only":observation_only,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check",action="store_true")
    parser.add_argument("--live",action="store_true")
    parser.add_argument("--write",action="store_true")
    args = parser.parse_args()
    cases, leakage = audit()
    oracle = MiniCOracle()
    final = [case for case in cases if case["partition"]=="final"]
    base = {
        "original_reference_checks":reference_checks(oracle,cases),
        "archived_normalization":archived(oracle),
        "ablation":static(final, STAGES),
        "calibration":{p:static([c for c in cases if c["partition"]==p], STAGES)
                       for p in ("development","selection","calibration")},
        "mechanisms":records(oracle,final),
    }
    history75 = json.loads((PHASE75_ROOT/"cases-v1.json").read_text())
    coprime = next(case for case in history75 if case["id"]=="coprime-count-fault")
    base["archived_coprime"] = run_projection(coprime,phase9=True).program_analysis["phase9"]
    if args.check:
        assert len(base["archived_normalization"])==4
        assert set(base["mechanisms"]["new_categories"]) == CATEGORIES
        assert base["archived_coprime"]["status"] == "UNSUPPORTED_PROJECTION"
    reports = {"phase9-audit-v1":leakage,"phase9-static-v1":base}
    if args.live:
        result = isolated(final)
        if args.check:
            assert result["metrics"]["9"]["false_alerts"]["hits"]==0
            assert result["by_provenance"]["9"]["adapted_real_defect"]["count"]==len(leakage["external_families"])
        reports["phase9-live-v1"] = result
    if args.write:
        for filename,report in reports.items():
            (REPORTS/f"{filename}.json").write_text(json.dumps(report,indent=2,ensure_ascii=False)+"\n")
    print(json.dumps({
        "audit":leakage,
        "static": {name:results["guided_metrics"] for name,results in base["ablation"].items() if "guided_metrics" in results},
        **({"isolated":reports["phase9-live-v1"]["metrics"]} if args.live else {}),
    },indent=2))


if __name__ == "__main__":
    main()
