"""Evaluate the shipped compiler and repair pipeline on the frozen Phase 1 corpus."""

import argparse
import hashlib
import json
import math
import platform
import statistics
from importlib.metadata import version
from pathlib import Path
from time import perf_counter_ns

from ai.correction_orchestrator import CorrectionOrchestrator
from ai.correction_safety import repair_key
from ai.error_predictor import ErrorPrediction, MLCorrectionPredictor
from ai.llm_fallback import OllamaFallbackService
from compiler.compound_recovery import generate_compound_candidates
from compiler.semantic_analyzer import analyze_source_semantics

from .corpus import ROOT, load_cases, overlapping_cases

MODEL = ROOT / "models" / "syntax_error_classifier.joblib"
SEED = 42  # Used to construct the frozen synthetic corpus.


class NoPredictor:
    def predict_error_type(self, context):
        return ErrorPrediction("UNCLASSIFIED", 0.0, {})


class RuleOnly(CorrectionOrchestrator):
    """Native compiler candidate order and context tie-breaks with no learned scores."""

    def _generate_ml_candidates(self, source, diagnostic, context, prediction):
        return ()

    def _syntax_candidates(self, source, baseline, diagnostic, context, prediction):
        return (
            *diagnostic.correction_candidates,
            *generate_compound_candidates(source, baseline.tokens, baseline.syntax_errors, diagnostic),
        )


class MLOnly(CorrectionOrchestrator):
    def _syntax_candidates(self, source, baseline, diagnostic, context, prediction):
        return self._generate_ml_candidates(source, diagnostic, context, prediction)


def audit_source(source):
    analysis = analyze_source_semantics(source)
    return {
        "lexical": len(analysis.parse_result.lexical_errors),
        "syntax": len(analysis.parse_result.syntax_errors),
        "semantic": len(analysis.semantic_result.diagnostics) if analysis.semantic_result else None,
        "valid": analysis.success,
    }


def ranked_proposals(result):
    if not result.history:
        return []
    entry = result.history[0]
    proposals = []
    seen = set()
    for validation in [entry.validation, *(attempt.validation for attempt in entry.attempts)]:
        if validation is None or not validation.relevant_valid:
            continue
        candidate = validation.corrected_source
        key = repair_key(candidate)
        if candidate != result.original_source and key not in seen:
            seen.add(key)
            proposals.append(candidate)
    return proposals[:3]


def intention_outcome(case, proposal, valid):
    if case["unambiguous"] is False:
        return "AMBIGUOUS_INTENT"
    if proposal is None or not valid:
        return "UNKNOWN_INTENT"
    if repair_key(proposal) in {repair_key(source) for source in case["acceptable_sources"]}:
        return "CORRECT_INTENT_RECOVERY"
    if repair_key(proposal) in {repair_key(source) for source in case["rejected_sources"]}:
        return "INCORRECT_INTENT_RECOVERY"
    return "UNKNOWN_INTENT"


def evaluate_case(case, orchestrator, repeats):
    source = case["source"]
    if not case["minic_supported"]:
        return {**case, "status": "UNSUPPORTED_MINIC"}
    baseline = audit_source(source)
    timings = []
    for _ in range(repeats):
        start = perf_counter_ns()
        result = orchestrator.correct(source)
        timings.append((perf_counter_ns() - start) / 1_000_000)

    proposals = ranked_proposals(result)
    ranked = [{"source": proposal, "compiler": audit_source(proposal)} for proposal in proposals]
    expected = {repair_key(reference) for reference in case["acceptable_sources"]}
    matches = [repair_key(item["source"]) in expected for item in ranked]
    top = proposals[0] if proposals else None
    top_valid = bool(ranked and ranked[0]["compiler"]["valid"])
    outcome = intention_outcome(case, top, top_valid)
    prediction = result.predictions[0].label if result.predictions else None
    if prediction == "UNCLASSIFIED":
        prediction = None
    return {
        **case,
        "status": "UNSUPPORTED_LOGIC_DETECTION" if case["detection_scope"] == "logic" else "EVALUATED",
        "detected": not baseline["valid"],
        "original_compiler": baseline,
        "prediction": prediction,
        "ranked_proposals": ranked,
        "top1_match": bool(matches and matches[0]),
        "top3_match": any(matches),
        "exact_match": top in case["acceptable_sources"],
        "top1_valid": top_valid,
        "intention_outcome": outcome,
        "behavioral_equivalence": "UNVERIFIED",
        "automatically_changed": result.corrected_source != source,
        "automatically_corrected": result.corrected_source != source and repair_key(result.corrected_source) in expected,
        "automatic_output": result.corrected_source,
        "decision": result.stop_reason,
        "safety": result.history[0].to_dict()["safety"] if result.history else None,
        "ollama_attempts": sum(
            bool(entry.llm_fallback and entry.llm_fallback.attempted)
            + bool(entry.ambiguity_selection and entry.ambiguity_selection.attempted)
            for entry in result.history
        ),
        "latency_ms": timings,
    }


def ratio(numerator, denominator):
    return {"numerator": numerator, "denominator": denominator, "value": numerator / denominator if denominator else None}


def metrics(rows, classification):
    rows = [row for row in rows if row["status"] != "UNSUPPORTED_MINIC"]
    faults = [row for row in rows if row["has_error"]]
    predicted = [row for row in rows if row["detected"]]
    positives = sum(row["detected"] for row in faults)
    known = [row for row in faults if row["unambiguous"] and row["acceptable_sources"]]
    labels = [row for row in faults if row["expected_class"]] if classification else []
    proposed = [row for row in rows if row["ranked_proposals"]]
    assessable = [
        row for row in proposed if row["top1_valid"]
        and row["intention_outcome"] in {"CORRECT_INTENT_RECOVERY", "INCORRECT_INTENT_RECOVERY"}
    ]
    ambiguous = [row for row in faults if not row["unambiguous"]]
    controls = [row for row in rows if not row["has_error"]]
    latency = sorted(sample for row in faults for sample in row["latency_ms"])
    compiler_faults = [row for row in faults if row["detection_scope"] == "compiler"]
    return {
        "detection_precision": ratio(positives, len(predicted)),
        "detection_recall": ratio(positives, len(faults)),
        "compiler_fault_detection_recall": ratio(sum(row["detected"] for row in compiler_faults), len(compiler_faults)),
        "classification_accuracy": ratio(sum(row["expected_class"] == row["prediction"] for row in labels), len(labels)),
        "exact_correction_match": ratio(sum(row["exact_match"] for row in known), len(known)),
        "top_1_repair_accuracy": ratio(sum(row["top1_match"] for row in known), len(known)),
        "top_3_repair_accuracy": ratio(sum(row["top3_match"] for row in known), len(known)),
        "compiler_valid_repair_rate": ratio(sum(row["top1_valid"] for row in proposed), len(proposed)),
        "intention_recovery_accuracy": ratio(sum(row["intention_outcome"] == "CORRECT_INTENT_RECOVERY" for row in known), len(known)),
        "incorrect_repair_rate": ratio(sum(row["intention_outcome"] == "INCORRECT_INTENT_RECOVERY" for row in assessable), len(assessable)),
        "behavioral_equivalence_verified": ratio(0, len(proposed)),
        "ambiguous_case_abstention_rate": ratio(sum(not row["automatically_changed"] for row in ambiguous), len(ambiguous)),
        "automatic_intended_repair_rate": ratio(sum(row["automatically_corrected"] for row in known), len(known)),
        "regression_count": {"count": sum(row["automatically_changed"] or row["detected"] for row in controls), "denominator": len(controls)},
        "average_correction_latency_ms": {"value": statistics.mean(latency) if latency else None, "denominator": len(latency)},
        "p95_correction_latency_ms": {"value": latency[math.ceil(.95 * len(latency)) - 1] if latency else None, "denominator": len(latency)},
    }


def run(cases, model_path=MODEL, repeats=3, *, ollama=True):
    if repeats < 1:
        raise ValueError("At least one timing sample per case is required")
    overlap = overlapping_cases(cases)
    if overlap:
        raise ValueError(f"Evaluation cases overlap archived training templates: {', '.join(overlap)}")
    model_hash = hashlib.sha256(model_path.read_bytes()).hexdigest() if model_path.is_file() else None
    predictor = None
    model_error = None
    try:
        predictor = MLCorrectionPredictor.load(model_path)
    except Exception as exc:
        model_error = f"Classifier unavailable ({type(exc).__name__})"
    model_classes = predictor.pipeline.named_steps["classifier"].classes_ if predictor is not None else ()
    service = OllamaFallbackService()
    ollama_available = ollama and predictor is not None and service.available
    configs = {
        "rule_based": (RuleOnly(NoPredictor()), None),
        "existing_ml": (MLOnly(predictor) if predictor is not None else None, model_error),
        "hybrid": (CorrectionOrchestrator(predictor) if predictor is not None else None, model_error),
        "ollama_assisted": (
            CorrectionOrchestrator(predictor, llm_fallback=service) if ollama_available else None,
            None if ollama_available else "Skipped by request" if not ollama else model_error or service.unavailable_reason,
        ),
    }
    result = {
        "schema_version": 1,
        "seed": SEED,
        "dataset_version": 1,
        "dataset_sha256": hashlib.sha256(json.dumps(cases, sort_keys=True).encode()).hexdigest(),
        "case_count": len(cases),
        "repeats": repeats,
        "environment": {
            "python": platform.python_version(),
            "dependencies": {name: version(name) for name in ("scikit-learn", "joblib", "numpy", "scipy", "fastapi", "ply")},
            "model_sha256": model_hash,
            "model_classes": len(model_classes),
            "ollama_model": service.model,
        },
        "modes": {},
    }
    categories = sorted({case["category"] for case in cases})
    for name, (orchestrator, error) in configs.items():
        if orchestrator is None:
            result["modes"][name] = {"available": False, "reason": error}
            continue
        rows = [evaluate_case(case, orchestrator, repeats) for case in cases]
        classification = name != "rule_based"
        result["modes"][name] = {
            "available": True,
            "metrics": metrics(rows, classification),
            "per_category": {category: metrics([row for row in rows if row["category"] == category], classification) for category in categories},
            "cases": rows,
            "ollama_attempts": sum(row.get("ollama_attempts", 0) for row in rows),
        }
    return result


def compare(modes):
    if not modes["existing_ml"]["available"]:
        return "The stored classifier was unavailable, so ML comparisons are unavailable."
    by_case = {name: {row["id"]: row for row in modes[name]["cases"]} for name in ("rule_based", "existing_ml", "hybrid")}
    rules, model, hybrid = (by_case[name] for name in ("rule_based", "existing_ml", "hybrid"))
    def improvement(left, right):
        return ", ".join(case_id for case_id in left if left[case_id].get("top1_match") and not right[case_id].get("top1_match")) or "none"
    logic = sum(row["status"] == "UNSUPPORTED_LOGIC_DETECTION" for row in hybrid.values())
    return (
        f"- ML-only top-1 matches missed by rule-based correction: {improvement(model, rules)}.\n"
        f"- Rule-based top-1 matches missed by ML-only correction: {improvement(rules, model)}.\n"
        f"- Hybrid top-1 matches missed by ML-only correction: {improvement(hybrid, model)}.\n"
        f"- {logic} valid Mini-C cases contained specification-level logic errors. General intent detection is unsupported.\n"
        "- Behavioral equivalence was not executed. A compiler-valid proposal can still change behavior."
    )


def display(metric):
    if "numerator" in metric:
        n, d = metric["numerator"], metric["denominator"]
        return f"{n}/{d}" if d else "N/A (0 eligible)"
    if "count" in metric:
        return f"{metric['count']}/{metric['denominator']}"
    return f"{metric['value']:.2f} ms ({metric['denominator']} samples)" if metric["value"] is not None else "N/A (0 samples)"


def write_reports(report, out):
    out.mkdir(parents=True, exist_ok=True)
    (out / "phase1-v1.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    lines = [
        "# Phase 1 benchmark", "",
        f"{report['case_count']} frozen cases, corpus v{report['dataset_version']}, seed {report['seed']}.",
        "", compare(report["modes"]), "",
    ]
    for name, mode in report["modes"].items():
        lines.extend([f"## {name.replace('_', ' ').title()}", ""])
        if not mode["available"]:
            lines.extend([mode["reason"], ""])
            continue
        lines.extend(["| Metric | Result |", "|---|---:|"])
        lines.extend(f"| {key.replace('_', ' ')} | {display(value)} |" for key, value in mode["metrics"].items())
        lines.extend(["", "| Category | Detection recall | Top 1 | Top 3 | Compiler valid |", "|---|---:|---:|---:|---:|"])
        for category, values in mode["per_category"].items():
            cells = [display(values[key]) for key in ("detection_recall", "top_1_repair_accuracy", "top_3_repair_accuracy", "compiler_valid_repair_rate")]
            lines.append("| " + " | ".join([category.replace("_", " "), *cells]) + " |")
        lines.append("")
    (out / "phase1-v1.md").write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=ROOT / "benchmarks" / "reports")
    parser.add_argument("--model", type=Path, default=MODEL)
    parser.add_argument("--repeat", type=int, default=3)
    parser.add_argument("--no-ollama", action="store_true")
    args = parser.parse_args()
    if args.repeat < 1:
        parser.error("--repeat must be positive")
    report = run(load_cases(), args.model, args.repeat, ollama=not args.no_ollama)
    write_reports(report, args.out)
    print(f"Wrote benchmark reports to {args.out}")


if __name__ == "__main__":
    main()
