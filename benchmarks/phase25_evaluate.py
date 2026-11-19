"""Counterfactual evaluation separating candidates, ranking and supplied evidence."""

from __future__ import annotations

import argparse
from collections import Counter
from hashlib import sha256
import json
from math import ceil
from pathlib import Path
from statistics import mean
from time import perf_counter

from ai.correction_orchestrator import CorrectionOrchestrator
from ai.correction_safety import repair_key
from ai.error_predictor import MLCorrectionPredictor
from ai.intention_context import Requirement
from ai.intention_engine import analyze_intention
from ai.intention_learning import MODEL_PATH, load_expanded_ranker
from ai.intention_ranker import load_ranker

from .corpus import ROOT
from .phase2_evaluate import _wilson, historical_rows, legacy
from .phase25_data import DEVELOPMENT, FINAL
from .run import MODEL, MLOnly, NoPredictor, RuleOnly, audit_source, ratio


OUT = ROOT / "benchmarks" / "reports"
CODE_ONLY = ("rules", "original_ml", "original_hybrid", "phase2_deterministic", "phase2_learned",
             "expanded_deterministic", "expanded_learned", "full_code_only")


def old_cohort():
    yield from historical_rows()


def engine(case, mode, v1, v2):
    requirement = None
    if mode == "full_natural_language":
        requirement = Requirement(**case["natural"])
    elif mode == "full_explicit":
        requirement = Requirement(**case["explicit"])
    enhanced = not mode.startswith("phase2")
    start = perf_counter()
    result = analyze_intention(case["source"], requirement, enhanced=enhanced,
                               ranker=v1 if mode == "phase2_learned" else None,
                               expanded_ranker=v2 if mode in {"expanded_learned", "full_code_only", "full_natural_language", "full_explicit"} else None)
    latency = (perf_counter()-start)*1000
    return {
        "proposals": [c.proposed_code for c in result.candidates],
        "valid": [c.compiler_valid for c in result.candidates],
        "finding": result.finding, "decision": result.decision, "attempts": result.attempts,
        "requirement_status": result.requirement_status,
        "ranker_scored_candidates": sum(c.relative_score is not None for c in result.candidates),
        "applied": False, "applied_source": case["source"], "latency_ms": latency,
        "candidate_ms": result.candidate_ms,
    }


def evaluate_case(case, observed, mode):
    proposals = observed["proposals"]
    allowed = {repair_key(text) for text in case["accepted"]}
    banned = {repair_key(text) for text in case.get("rejected", [])}
    keys = [repair_key(text) for text in proposals]
    positions = [index for index, key in enumerate(keys) if key in allowed]
    kind = case.get("kind", "compiler")
    finding = observed["finding"]
    valid_proposals = observed.get("valid")
    if valid_proposals is None:
        valid_proposals = [audit_source(text)["valid"] for text in proposals]
    return {
        "id": case["id"], "family": case["family"], "category": case["category"], "kind": kind,
        "known": bool(allowed) and not case.get("ambiguous"),
        "ambiguous": bool(case.get("ambiguous")),
        "compile_fault": not audit_source(case["source"])["valid"],
        "logic_alert": finding in {"SPECIFICATION_SUPPORTED_SUSPICION", "HEURISTIC_SUSPICION"} and kind != "unsupported",
        "finding": finding, "decision": observed["decision"], "requirement_status": observed.get("requirement_status"),
        "input_evidence": case.get("natural") if mode == "full_natural_language" else case.get("explicit") if mode == "full_explicit" else None,
        "scored_candidates": observed.get("ranker_scored_candidates"),
        "first_match_rank": min(positions, default=-1) + 1,
        "top_rejected_reference": bool(keys and keys[0] in banned),
        "proposal_count": len(keys), "valid_count": sum(valid_proposals),
        "top_valid": bool(valid_proposals and valid_proposals[0]), "proposals": proposals,
        "applied": observed["applied"], "rejected_automatic": observed["applied"] and repair_key(observed["applied_source"]) in banned,
        "latency_ms": observed["latency_ms"], "candidate_ms": observed.get("candidate_ms"),
        "attempts": observed.get("attempts"),
    }


def timing(values):
    samples = sorted(value for value in values if value is not None)
    return {"n": len(samples), "mean": mean(samples) if samples else None,
            "p95": samples[ceil(.95*len(samples))-1] if samples else None}


def metrics(rows):
    supported = [r for r in rows if r["kind"] != "unsupported"]
    known = [r for r in supported if r["known"]]
    covered = [r for r in known if r["first_match_rank"]]
    compiler = [r for r in supported if r["kind"] == "compiler"]
    logic = [r for r in supported if r["kind"] == "logic"]
    control = [r for r in supported if r["kind"] == "control"]
    ambiguous = [r for r in supported if r["ambiguous"]]
    ambiguous_status = {"AMBIGUOUS", "INSUFFICIENT_CONTEXT", "NO_SUPPORTED_CORRECTION", "ambiguous_valid_candidates"}
    valid_trials = [r for r in supported if r["kind"] in {"logic", "control"}]
    alerts = [r for r in valid_trials if r["logic_alert"]]
    top_rank = sum(r["first_match_rank"] == 1 for r in known)
    known_proposed = [r for r in known if r["proposal_count"]]
    total_proposed = sum(r["proposal_count"] for r in supported)
    aut = [r for r in supported if r["applied"]]
    coverage = {}
    for label, accepted in (
        ("first_available", known_proposed),
        ("non_ambiguous_valid", [r for r in known_proposed if r["top_valid"] and r["decision"] not in ambiguous_status]),
        ("strong_requirement", [r for r in known_proposed if r["decision"] == "STRONG_SPECIFICATION_EVIDENCE"]),
    ):
        coverage[label] = {"coverage": ratio(len(accepted), len(known)),
                           "reference_accuracy": ratio(sum(r["first_match_rank"] == 1 for r in accepted), len(accepted))}
    return {
        "compiler_detection": ratio(sum(r["compile_fault"] for r in compiler), len(compiler)),
        "logic_precision_on_labeled_valid_cases": ratio(sum(r["kind"] == "logic" for r in alerts), len(alerts)),
        "logic_recall": ratio(sum(r["logic_alert"] for r in logic), len(logic)),
        "valid_control_alerts": ratio(sum(r["logic_alert"] for r in control), len(control)),
        "candidate_recall": ratio(len(covered), len(known)),
        "top_1": ratio(top_rank, len(known)), "top_1_wilson_95": _wilson(top_rank, len(known)),
        "intention_recovery_reference_match": ratio(top_rank, len(known)),
        "top_3": ratio(sum(0 < r["first_match_rank"] <= 3 for r in known), len(known)),
        "ranking_top1_given_candidate": ratio(top_rank, len(covered)),
        "missed_generation": ratio(len(known)-len(covered), len(known)),
        "generation_hit_ranked_lower": ratio(len(covered)-top_rank, len(known)),
        "top_reference_miss_when_proposed": ratio(sum(r["first_match_rank"] != 1 for r in known_proposed), len(known_proposed)),
        "explicit_wrong_reference": ratio(sum(r["top_rejected_reference"] for r in known_proposed), len(known_proposed)),
        "candidate_validity": ratio(sum(r["valid_count"] for r in supported), total_proposed),
        "candidates_per_supported_case": ratio(total_proposed, len(supported)),
        "ambiguous_flag": ratio(sum(r["decision"] in ambiguous_status for r in ambiguous), len(ambiguous)),
        "ambiguous_no_automatic_change": ratio(sum(not r["applied"] for r in ambiguous), len(ambiguous)),
        "automatic_changes": ratio(len(aut), len(supported)),
        "automatic_rejected_reference": ratio(sum(r["rejected_automatic"] for r in aut), len(aut)),
        "runtime_verification": ratio(0, 0),
        "decision_counts": dict(Counter(r["decision"] for r in supported)),
        "requirement_counts": dict(Counter(r["requirement_status"] for r in supported if r["requirement_status"])),
        "latency": timing(r["latency_ms"] for r in rows),
        "candidate_generation_and_validation": timing(r["candidate_ms"] for r in rows),
        "selective_accuracy": coverage,
    }


def report_rows(rows):
    return {"metrics": metrics(rows), "cases": rows, "per_category": {
        category: metrics([r for r in rows if r["category"] == category])
        for category in sorted({r["category"] for r in rows})
    }}


def run(cases, *, historical=None):
    predictor = MLCorrectionPredictor.load(MODEL)
    v1, status1 = load_ranker()
    load_expanded_ranker.cache_clear()
    start = perf_counter()
    v2, status2 = load_expanded_ranker()
    cold_ms = (perf_counter()-start)*1000
    policies = {"rules": RuleOnly(NoPredictor()), "original_ml": MLOnly(predictor),
                "original_hybrid": CorrectionOrchestrator(predictor)}
    report = {"version": 1, "artifacts": {
        "phase2_status": status1, "phase25_status": status2,
        "expanded_bytes": MODEL_PATH.stat().st_size if MODEL_PATH.is_file() else 0,
        "expanded_cold_load_ms": cold_ms, "activated_categories": v2.selected if v2 else {},
        "expanded_sha256": sha256(MODEL_PATH.read_bytes()).hexdigest() if MODEL_PATH.is_file() else None,
    }, "cohorts": {}}

    def one(mode, rows):
        results = []
        for case in rows:
            observed = legacy(case, policies[mode]) if mode in policies else engine(case, mode, v1, v2)
            results.append(evaluate_case(case, observed, mode))
        return report_rows(results)

    for name, rows in (("historical", historical), ("evaluation", cases)):
        if rows is None:
            continue
        configurations = {mode: one(mode, rows) for mode in CODE_ONLY[:-1]}
        configurations["full_code_only"] = configurations["expanded_learned"]
        report["cohorts"][name] = {"cases": len(rows), "families": len({r["family"] for r in rows}),
                                   "configurations": configurations}
    matched = [case for case in cases if case.get("natural") and case.get("explicit")]
    comparison = {mode: one(mode, matched) for mode in ("full_code_only", "full_natural_language", "full_explicit")}
    natural = comparison["full_natural_language"]["cases"]
    report["evidence_comparison"] = {"cases": len(matched), "configurations": comparison, "natural_by_status": {
        status: metrics([r for r in natural if r["requirement_status"] == status])
        for status in sorted({r["requirement_status"] for r in natural if r["requirement_status"]})
    }}
    return report


def stable(data):
    if isinstance(data, dict):
        return {key: stable(value) for key, value in data.items()
                if key not in {"latency_ms", "candidate_ms", "candidate_generation_and_validation", "latency", "expanded_cold_load_ms"}}
    if isinstance(data, list):
        return list(map(stable, data))
    return data


def fraction(value):
    return f"{value['numerator']}/{value['denominator']}"


def write(report, out):
    out.mkdir(parents=True, exist_ok=True)
    (out / "phase25-evaluation-v1.json").write_text(json.dumps(report, indent=2) + "\n")
    lines = ["# Phase 2.5 evaluation", "", "Reference matches and compiler validity are static observations.", ""]
    cohorts = {**report["cohorts"], "Matched evidence comparison": report["evidence_comparison"]}
    for name, cohort in cohorts.items():
        lines.extend([f"## {name.title()} ({cohort['cases']} cases)", "",
                      "| Mode | Recall | Top 1 | Top 3 | Logic precision / recall | Mean / p95 ms |",
                      "|---|---:|---:|---:|---:|---:|"])
        for mode, values in cohort["configurations"].items():
            m = values["metrics"]
            cells = [fraction(m[key]) for key in ("candidate_recall", "top_1", "top_3")]
            cells.append(f"{fraction(m['logic_precision_on_labeled_valid_cases'])} / {fraction(m['logic_recall'])}")
            latency = m["latency"]
            cells.append(f"{latency['mean']:.2f} / {latency['p95']:.2f}" if latency["n"] else "N/A")
            lines.append("| " + " | ".join([mode, *cells]) + " |")
        lines.append("")
    (out / "phase25-evaluation-v1.md").write_text("\n".join(lines).rstrip() + "\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path)
    parser.add_argument("--development", action="store_true", help="score development cases without opening the frozen final dataset")
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    if args.development and args.out is None:
        parser.error("Use --out to keep development output separate from frozen reports.")
    path = DEVELOPMENT if args.development else FINAL
    cases = json.loads(path.read_text())["cases"]
    if args.development:
        cases = [case for case in cases if case["split"] == "development"]
    report = run(cases, historical=None if args.development else list(old_cohort()))
    report["dataset_sha256"] = sha256(path.read_bytes()).hexdigest()
    out = args.out or OUT
    if args.check:
        if stable(report) != stable(json.loads((out / "phase25-evaluation-v1.json").read_text())):
            raise SystemExit("Phase 2.5 decisions differ from the stored evidence")
        print("Phase 2.5 decisions reproduce.")
    else:
        write(report, out)
