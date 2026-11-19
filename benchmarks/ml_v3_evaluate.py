"""Compare frozen engine versions, shared pools and requirement evidence."""
import argparse
from hashlib import sha256
import json
from time import perf_counter

from ai.intention_context import Requirement
from ai.intention_engine import analyze_intention, order_candidates
from ai.intention_learning import load_expanded_ranker
from ai.intention_v3_ranker import load_generalized_ranker, MODEL

from .corpus import ROOT
from .ml_v3_data import DEVELOPMENT, FINAL, read
from .phase2_evaluate import _wilson
from .phase25_evaluate import evaluate_case, report_rows, run as baseline, stable

REPORT = ROOT / "benchmarks/reports/ml-v3-evaluation-v1.json"


def timed_generation(case, mode, *, new_generation=True):
    requirement = Requirement(**case[mode]) if mode in {"natural", "explicit"} else None
    start = perf_counter()
    result = analyze_intention(case["source"], requirement, generalized=True, generation_v3=new_generation)
    return result, (perf_counter() - start) * 1000


def observed(case, result, mode, elapsed, *, ranker=None, method=None):
    start = perf_counter()
    choices = order_candidates(result.candidates, None, expanded=ranker, experimental=method, generalized=True)
    return evaluate_case(case, {
        "proposals": [item.proposed_code for item in choices], "valid": [item.compiler_valid for item in choices],
        "finding": result.finding, "decision": result.decision, "requirement_status": result.requirement_status,
        "scored_candidates": sum(item.relative_score is not None for item in choices),
        "applied": False, "applied_source": case["source"], "attempts": result.attempts,
        "latency_ms": elapsed + (perf_counter() - start) * 1000, "candidate_ms": result.candidate_ms,
    }, {"natural": "full_natural_language", "explicit": "full_explicit"}.get(mode, mode))


def with_intervals(configuration):
    for category, view in [(None, configuration["metrics"]), *configuration["per_category"].items()]:
        rows = [row for row in configuration["cases"] if category is None or row["category"] == category]
        for name in ("top_3", "candidate_recall", "logic_recall", "logic_precision_on_labeled_valid_cases",
                     "valid_control_alerts", "top_reference_miss_when_proposed"):
            part = view[name]
            view[name + "_wilson_95"] = _wilson(part["numerator"], part["denominator"])
        valid_controls = [row for row in rows if row["kind"] == "control" and not row["ambiguous"] and not row["compile_fault"]]
        false_alerts = sum(row["logic_alert"] for row in valid_controls)
        view["confirmed_valid_control_alerts"] = {
            "count": false_alerts, "total": len(valid_controls), "wilson_95": _wilson(false_alerts, len(valid_controls)),
        }
        view["no_candidate_abstention"] = [
            sum(row["proposal_count"] == 0 for row in rows), len(rows),
        ]
    return configuration


def run(cases):
    previous = baseline(cases)["cohorts"]["evaluation"]["configurations"]
    ranker, ranking_status = load_generalized_ranker()
    v2 = load_expanded_ranker()[0]
    output = {}
    names = {"deterministic_v3": (None, None), "v2_on_v3_pool": (v2, None),
             "pointwise_v3_experiment": (ranker, "pointwise"), "pairwise_v3_experiment": (ranker, "pairwise"),
             "boosted_v3_experiment": (ranker, "boosted"), "learned_v3_gated": (ranker, None)}
    rows = {name: [] for name in (*names, "v3_without_generation")}
    guided = {name: [] for name in ("code_only", "natural", "explicit")}
    for case in cases:
        result, elapsed = timed_generation(case, "code_only")
        for name, (model, method) in names.items():
            rows[name].append(observed(case, result, "code_only", elapsed, ranker=model, method=method))
        # Equal membership across every v3 ranking counterfactual.
        membership = sorted(rows["deterministic_v3"][-1]["proposals"])
        assert all(sorted(rows[name][-1]["proposals"]) == membership for name in names)
        ablation, ms = timed_generation(case, "code_only", new_generation=False)
        rows["v3_without_generation"].append(observed(case, ablation, "code_only", ms))
        if case.get("natural") and case.get("explicit"):
            guided["code_only"].append(rows["learned_v3_gated"][-1])
            for mode in ("natural", "explicit"):
                result, ms = timed_generation(case, mode)
                guided[mode].append(observed(case, result, mode, ms, ranker=ranker))
    output.update({name: with_intervals(config) for name, config in previous.items()})
    output.update({name: with_intervals(report_rows(value)) for name, value in rows.items()})
    return {"version": 1, "cases": len(cases), "families": len({case["family"] for case in cases}),
            "artifact_sha256": sha256(MODEL.read_bytes()).hexdigest(), "ranking_status": ranking_status,
            "configurations": output, "full_pipeline": {name: with_intervals(report_rows(value)) for name, value in guided.items()}}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--development", action="store_true")
    mode.add_argument("--write", action="store_true")
    mode.add_argument("--check", action="store_true")
    args = parser.parse_args()
    cases = read(DEVELOPMENT if args.development else FINAL)
    report = run([case for case in cases if case["split"] == "development"] if args.development else cases)
    if args.write:
        REPORT.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    elif args.check and stable(report) != stable(json.loads(REPORT.read_text())):
        raise SystemExit("ML v3 decisions differ from the checked-in report.")
    print(json.dumps({section: {name: {
        key: row["metrics"][key] for key in ("candidate_recall", "top_1", "top_3", "logic_recall", "valid_control_alerts")
    } for name, row in report[section].items()} for section in ("configurations", "full_pipeline")}, indent=2))
