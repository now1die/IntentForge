"""Replay the frozen v3 errors and compare v4 using identical candidate pools."""
import argparse
import json
from time import perf_counter

from ai.intention_context import Requirement
from ai.intention_engine import analyze_intention, order_candidates
from ai.intention_learning import load_expanded_ranker
from ai.intention_v3_ranker import load_generalized_ranker

from .ml_v3_data import read
from .phase25_evaluate import evaluate_case, metrics, stable
from .phase35_data import FINAL

REPORT = FINAL.parent.parent / "reports" / "phase35-evaluation-v1.json"
V3_REPORT = REPORT.with_name("ml-v3-evaluation-v1.json")
FAILURE_EXPLANATIONS = {
    "log_update": "Pair exists below a single-edit alternative",
    "reset_shift": "Multiple compatible bool bindings",
    "joined_alpha": "Multiple compatible return bindings",
    "cell_selection": "Index behavior needs a specification",
    "exclusion_band": "No specification for inclusive versus exclusive comparison",
    "negated_latch": "No evidence for a Boolean negation",
    "charged_meter": "Accumulator arithmetic intent is unavailable",
    "ordered_blend": "Same-typed arguments provide no unique order",
    "join_boundary": "No specification supports choosing AND over OR",
    "armstrong_partial_digit_power": "Equality direction depends on the algorithm specification",
    "resistor_numeric_lookup": "Repeated index alone does not establish the intended band",
    "series_numeric_slice_cell": "Index arithmetic depends on the slice specification",
    "control_intentional_rollover": "An intentional alternate return appears inconsistent",
}


def historical_taxonomy():
    rows = json.loads(V3_REPORT.read_text())["configurations"]["learned_v3_gated"]["cases"]
    return [{
        "case": row["id"], "category": row["category"],
        "type": "false_positive" if not row["known"] else
        "ordering" if row["first_match_rank"] else "missing_candidate",
        "observation": FAILURE_EXPLANATIONS[row["id"]],
        "reference_changed": False,
    } for row in rows if (row["known"] and row["first_match_rank"] != 1)
            or (row["kind"] == "control" and row["logic_alert"])]


def generation(row, *, phase35, mode="code_only"):
    requirement = Requirement(**row[mode]) if mode != "code_only" else None
    start = perf_counter()
    result = analyze_intention(row["source"], requirement, generalized=True, phase35=phase35)
    return result, (perf_counter() - start) * 1000


def observe(row, result, elapsed, mode, ranker=None, method=None):
    start = perf_counter()
    choices = order_candidates(result.candidates, None, expanded=ranker, experimental=method, generalized=True)
    from ai.intention_uncertainty import classify
    recommendation = classify(choices[0], ambiguous=result.decision == "AMBIGUOUS")["recommendation"] if choices else "ABSTAIN"
    return {"recommendation": recommendation, **evaluate_case(row, {
        "proposals": [item.proposed_code for item in choices],
        "valid": [item.compiler_valid for item in choices], "finding": result.finding,
        "decision": result.decision, "requirement_status": result.requirement_status,
        "applied": False, "applied_source": row["source"], "attempts": result.attempts,
        "latency_ms": elapsed + (perf_counter() - start) * 1000, "candidate_ms": result.candidate_ms,
    }, {"natural": "full_natural_language", "explicit": "full_explicit"}.get(mode, mode))}


def report(rows):
    keys = ("top_1", "top_3", "candidate_recall", "candidate_validity", "logic_recall",
            "valid_control_alerts", "logic_precision_on_labeled_valid_cases", "latency")
    control = [row for row in rows if row["kind"] == "control" and not row["ambiguous"] and not row["compile_fault"]]
    return {"metrics": metrics(rows),
            "confirmed_valid_alerts": [sum(row["logic_alert"] for row in control), len(control)],
            "abstained_recommendations": [sum(row["recommendation"] == "ABSTAIN" for row in rows), len(rows)],
            "per_category": {category: {key: value for key, value in
                metrics([row for row in rows if row["category"] == category]).items() if key in keys}
                for category in sorted({row["category"] for row in rows})}, "cases": rows}


def run():
    cases = read(FINAL)
    v2, v3, v4 = load_expanded_ranker()[0], load_generalized_ranker()[0], load_generalized_ranker(4)[0]
    if not v4:
        raise ValueError("The versioned v4 artifact is required for this evaluation")
    orderings = {"v4_deterministic": (None, None), "v2_same_pool": (v2, None), "v3_same_pool": (v3, None),
                 "v4_pointwise": (v4, "pointwise"), "v4_pairwise": (v4, "pairwise"),
                 "v4_boosted": (v4, "boosted"), "v4_deployed": (v4, None)}
    scores = {key: [] for key in ("v3_baseline", *orderings)}
    guided = {mode: [] for mode in ("code_only", "natural", "explicit")}
    for row in cases:
        baseline, elapsed = generation(row, phase35=False)
        scores["v3_baseline"].append(observe(row, baseline, elapsed, "code_only", v3))
        new, elapsed = generation(row, phase35=True)
        for name, (ranker, method) in orderings.items():
            scores[name].append(observe(row, new, elapsed, "code_only", ranker, method))
        pool = set(scores["v4_deterministic"][-1]["proposals"])
        assert all(set(scores[name][-1]["proposals"]) == pool for name in orderings)
        if row.get("natural") and row.get("explicit"):
            guided["code_only"].append(scores["v4_deployed"][-1])
            for mode in ("natural", "explicit"):
                new, elapsed = generation(row, phase35=True, mode=mode)
                guided[mode].append(observe(row, new, elapsed, mode, v4))
    external = {case["id"] for case in cases if "external_task" in case}
    return {"version": 1, "families": len({row["family"] for row in cases}),
            "configurations": {key: report(rows) for key, rows in scores.items()},
            "guided": {key: report(rows) for key, rows in guided.items()},
            "external": {key: report([row for row in rows if row["id"] in external])
                         for key, rows in scores.items() if key in {"v3_baseline", "v4_deployed"}},
            "historical_taxonomy": historical_taxonomy()}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--write", action="store_true")
    mode.add_argument("--check", action="store_true")
    args = parser.parse_args()
    result = run()
    if args.write:
        REPORT.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    elif stable(result) != stable(json.loads(REPORT.read_text())):
        raise SystemExit("Phase 3.5 benchmark decisions differ.")
    print(f"Verified Phase 3.5 evidence across {result['families']} final families.")
