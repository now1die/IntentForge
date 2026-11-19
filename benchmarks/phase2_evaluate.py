"""Evaluate existing pipelines and the Phase 2 generator/ranker on frozen cohorts."""

from __future__ import annotations

import argparse
from collections import Counter
from hashlib import sha256
import json
from math import ceil, sqrt
from pathlib import Path
from statistics import mean
from time import perf_counter

from ai.correction_options import suggest_correction_options
from ai.correction_orchestrator import CorrectionOrchestrator
from ai.correction_safety import repair_key
from ai.error_predictor import MLCorrectionPredictor
from ai.intention_engine import analyze_intention
from ai.intention_ranker import MODEL_PATH, load_ranker
from backend.app.routes.intention import RequirementRequest

from .corpus import ROOT, load_cases
from .phase2_data import FINAL
from .run import MLOnly, MODEL, NoPredictor, RuleOnly, audit_source, ratio


OUT = ROOT / "benchmarks" / "reports"
MODES = (
    "rules", "original_ml", "original_hybrid", "context_deterministic",
    "context_learned", "full_intention",
)


def historical_rows():
    for case in load_cases(corpus="all"):
        kind = ("unsupported" if not case["minic_supported"] else "control" if not case["has_error"]
                else "logic" if case["detection_scope"] == "logic" else "compiler")
        yield {"id": case["id"], "family": case["mutation_family"], "category": case["category"],
               "kind": kind, "ambiguous": not case["unambiguous"], "source": case["source"],
               "accepted": case["acceptable_sources"], "rejected": case["rejected_sources"],
               "requirement": None}


def legacy(case, orchestrator, predictor=None):
    source = case["source"]
    start = perf_counter()
    result = orchestrator.correct(source)
    ms = (perf_counter() - start) * 1000
    entry = result.history[0] if result.history else None
    validations = [entry.validation, *(attempt.validation for attempt in entry.attempts)] if entry else []
    # Dedupe the same first-diagnostic proposals as Phase 1 before taking top-k.
    unique = {}
    for validation in validations:
        if validation and validation.relevant_valid and validation.corrected_source != source:
            unique.setdefault(repair_key(validation.corrected_source), validation.corrected_source)
    ui = None
    if predictor is not None:
        options = suggest_correction_options(source, predictor, use_ollama=False)["options"]
        ui = [item["corrected_code"] for item in options if item["fully_valid"]]
        if result.fully_syntactically_valid and result.corrected_source != source:
            ui.append(result.corrected_source)
        last = result.history[-1] if result.history else None
        if not options and last and last.validation and last.validation.valid:
            ui.append(last.validation.corrected_source)
    return {
        "proposals": list(unique.values()), "ui": ui,
        "finding": "COMPILER_ERROR" if result.predictions or not result.fully_syntactically_valid else "NO_SUPPORTED_MISMATCH",
        "decision": result.stop_reason, "applied": result.corrected_source != source,
        "applied_source": result.corrected_source, "latency_ms": ms,
    }


def new(case, ranker, status, mode):
    requirement = None
    if mode == "full_intention" and case.get("requirement"):
        requirement = RequirementRequest.model_validate(case["requirement"]).to_domain()
    start = perf_counter()
    result = analyze_intention(case["source"], requirement, ranker=ranker, ranking_status=status)
    ms = (perf_counter() - start) * 1000
    return {
        "proposals": [candidate.proposed_code for candidate in result.candidates],
        "ui": [candidate.proposed_code for candidate in result.candidates if candidate.compiler_valid] if mode == "full_intention" else None,
        "finding": result.finding, "decision": result.decision, "ranking": result.ranking,
        "applied": False, "applied_source": case["source"], "latency_ms": ms,
    }


def _score(case, output):
    accepted = {repair_key(reference) for reference in case["accepted"]}
    rejected = {repair_key(reference) for reference in case.get("rejected", [])}
    ranked = [repair_key(text) for text in output["proposals"]]
    known = bool(accepted) and not case["ambiguous"]
    top = ranked[0] if ranked else None
    top_valid = bool(ranked) and audit_source(output["proposals"][0])["valid"]
    match = top in accepted and top_valid and known
    applied_key = repair_key(output["applied_source"]) if output["applied"] else None
    return {
        "id": case["id"], "category": case["category"], "kind": case["kind"], "known": known,
        "requirement_available": bool(case.get("requirement")), "ambiguous": case["ambiguous"],
        "detected_compiler_fault": not audit_source(case["source"])["valid"],
        "finding": output["finding"], "decision": output["decision"], "ranking": output.get("ranking"),
        "top_1": bool(match), "top_3": known and any(key in accepted for key in ranked[:3]),
        "candidate_hit": known and any(key in accepted for key in ranked),
        "proposal_count": len(ranked), "top_valid": top_valid,
        "intention_outcome": ("AMBIGUOUS" if case["ambiguous"] else "REFERENCE_MATCH" if match
                              else "REJECTED_REFERENCE" if top in rejected and top_valid else "UNKNOWN_INTENT"),
        "ui_hit": None if output["ui"] is None else known and any(repair_key(text) in accepted for text in output["ui"]),
        "applied": output["applied"], "auto_nonreference": bool(applied_key is not None and known and applied_key not in accepted),
        "auto_rejected_reference": applied_key in rejected, "proposals": output["proposals"],
        "latency_ms": output["latency_ms"],
    }


def _wilson(n, d):
    if not d:
        return None
    p = n / d
    z = 1.96
    center = (p + z*z/(2*d)) / (1+z*z/d)
    radius = z * sqrt((p*(1-p)+z*z/(4*d))/d) / (1+z*z/d)
    return [max(0, center-radius), min(1, center+radius)]


def metrics(rows):
    supported = [row for row in rows if row["kind"] != "unsupported"]
    known = [row for row in supported if row["known"]]
    recall = [row for row in known if row["candidate_hit"]]
    compiler = [row for row in supported if row["kind"] == "compiler"]
    logic = [row for row in supported if row["kind"] == "logic"]
    specified_logic = [row for row in logic if row["requirement_available"]]
    control = [row for row in supported if row["kind"] == "control"]
    proposals = [row for row in supported if row["proposal_count"]]
    ui = [row for row in known if row["ui_hit"] is not None]
    ambiguous = [row for row in supported if row["ambiguous"]]
    autos = [row for row in supported if row["applied"]]
    scores = sorted(row["latency_ms"] for row in rows)
    top = sum(row["top_1"] for row in known)
    return {
        "compiler_fault_detection": ratio(sum(row["detected_compiler_fault"] for row in compiler), len(compiler)),
        "logic_suspicion_detection": ratio(sum(row["finding"] == "SPECIFICATION_SUPPORTED_SUSPICION" for row in logic), len(logic)),
        "supplied_logic_suspicion_detection": ratio(sum(row["finding"] == "SPECIFICATION_SUPPORTED_SUSPICION" for row in specified_logic), len(specified_logic)),
        "control_specification_false_positives": ratio(sum(row["finding"] == "SPECIFICATION_SUPPORTED_SUSPICION" for row in control), len(control)),
        "control_heuristic_alerts": ratio(sum(row["finding"] == "HEURISTIC_SUSPICION" for row in control), len(control)),
        "top_1": ratio(top, len(known)),
        "top_1_wilson_95": _wilson(top, len(known)),
        "top_3": ratio(sum(row["top_3"] for row in known), len(known)),
        "known_intention_recovery": ratio(top, len(known)),
        "candidate_recall": ratio(len(recall), len(known)),
        "ranking_top_1_given_candidate": ratio(sum(row["top_1"] for row in recall), len(recall)),
        "compiler_valid_top_proposal": ratio(sum(row["top_valid"] for row in proposals), len(proposals)),
        "reviewable_accepted_ui_repairs": ratio(sum(row["ui_hit"] for row in ui), len(ui)),
        "ambiguous_auto_abstention": ratio(sum(not row["applied"] for row in ambiguous), len(ambiguous)),
        "ambiguous_decision_or_no_supported_repair": ratio(
            sum(row["decision"] in {"AMBIGUOUS", "INSUFFICIENT_CONTEXT", "NO_SUPPORTED_CORRECTION", "ambiguous_valid_candidates"}
                for row in ambiguous), len(ambiguous)),
        "automatic_changes": ratio(len(autos), len(supported)),
        "automatic_non_reference_among_adjudicable_outputs": ratio(sum(row["auto_nonreference"] for row in autos), sum(row["known"] for row in autos)),
        "automatic_explicitly_rejected": ratio(sum(row["auto_rejected_reference"] for row in autos), len(autos)),
        "behavioral_verification": ratio(0, 0),
        "inference_latency_ms": {"mean": mean(scores) if scores else None, "p95": scores[ceil(.95*len(scores))-1] if scores else None, "n": len(scores)},
        "intention_outcomes": dict(Counter(row["intention_outcome"] for row in supported)),
    }


def coverage(rows):
    known = [row for row in rows if row["known"]]
    # Prespecified evidence policies. Neither is fitted to final outcomes.
    decisions = {
        "show_first_available": [row for row in known if row["proposal_count"]],
        "compiler_valid_first_only": [row for row in known if row["top_valid"]],
        "strong_specification_only": [row for row in known if row["decision"] == "STRONG_SPECIFICATION_EVIDENCE"],
    }
    return {key: {"coverage": ratio(len(selected), len(known)),
                  "reference_accuracy": ratio(sum(row["top_1"] for row in selected), len(selected))}
            for key, selected in decisions.items()}


def stable(value):
    if isinstance(value, dict):
        return {key: stable(item) for key, item in value.items() if key not in {"latency_ms", "inference_latency_ms"}}
    if isinstance(value, list):
        return [stable(item) for item in value]
    return value


def run(historical, final, *, model_path=MODEL_PATH):
    predictor = MLCorrectionPredictor.load(MODEL)
    policies = {"rules": RuleOnly(NoPredictor()), "original_ml": MLOnly(predictor),
                "original_hybrid": CorrectionOrchestrator(predictor)}
    ranker, status = load_ranker(model_path)
    report = {"version": 1, "ranker": ranker.version if ranker else status, "calibration": "UNCALIBRATED_RELATIVE_SCORES",
              "frozen_final_sha256": sha256(FINAL.read_bytes()).hexdigest(), "cohorts": {}}
    for cohort, cases in (("historical", historical), ("final", final)):
        results = {}
        for mode in MODES:
            rows = []
            for case in cases:
                if mode in policies:
                    output = legacy(case, policies[mode], predictor if mode == "original_hybrid" else None)
                else:
                    active = ranker if mode != "context_deterministic" else None
                    output = new(case, active, status if mode != "context_deterministic" else "DETERMINISTIC", mode)
                rows.append(_score(case, output))
            categories = sorted({row["category"] for row in rows})
            results[mode] = {"metrics": metrics(rows), "coverage": coverage(rows),
                             "per_category": {category: metrics([row for row in rows if row["category"] == category])
                                              for category in categories}, "cases": rows}
        report["cohorts"][cohort] = {"cases": len(cases), "modes": results}
    return report


def _fraction(value):
    return f"{value['numerator']}/{value['denominator']}"


def write(report, out):
    out.mkdir(parents=True, exist_ok=True)
    (out / "phase2-evaluation-v1.json").write_text(json.dumps(report, indent=2) + "\n")
    lines = ["# Phase 2 frozen evaluation", "", f"Ranker: `{report['ranker']}`.",
             "Behavioral runtime observations: 0.", ""]
    for cohort, data in report["cohorts"].items():
        lines.extend([f"## {cohort.title()} ({data['cases']} cases)", "",
                      "| Configuration | Top 1 | Top 3 | Candidate recall | Rank success given candidate | Valid top | Mean / p95 ms |",
                      "|---|---:|---:|---:|---:|---:|---:|"])
        for name, row in data["modes"].items():
            measures = row["metrics"]
            latency = measures["inference_latency_ms"]
            values = [_fraction(measures[key]) for key in ("top_1","top_3","candidate_recall",
                      "ranking_top_1_given_candidate","compiler_valid_top_proposal")]
            lines.append("| " + " | ".join([name.replace("_"," "), *values, f"{latency['mean']:.2f} / {latency['p95']:.2f}"]) + " |")
        lines.append("")
    (out / "phase2-evaluation-v1.md").write_text("\n".join(lines).rstrip() + "\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=OUT)
    parser.add_argument("--model", type=Path, default=MODEL_PATH)
    parser.add_argument("--check", action="store_true", help="compare stable decisions against the committed report")
    args = parser.parse_args()
    report = run(list(historical_rows()), json.loads(FINAL.read_text())["cases"], model_path=args.model)
    if args.check:
        committed = json.loads((args.out / "phase2-evaluation-v1.json").read_text())
        if stable(report) != stable(committed):
            raise SystemExit("Phase 2 decisions differ from the committed report")
        print("Phase 2 historical and final decisions reproduce.")
    else:
        write(report, args.out)
