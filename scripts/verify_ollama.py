"""Probe local Ollama and check a real structured edit when the model is reachable."""

import argparse
import json
from pathlib import Path
from time import perf_counter

from ai.correction_orchestrator import CorrectionOrchestrator
from ai.correction_safety import assess_repair, repair_key
from ai.error_context import ErrorContext
from ai.error_predictor import MLCorrectionPredictor
from ai.llm_fallback import OllamaFallbackService
from benchmarks.corpus import ROOT, load_cases
from compiler.parser import parse
from compiler.semantic_analyzer import analyze_source_semantics


def verify(service):
    start = perf_counter()
    available = service.available
    report = {
        "model": service.model,
        "available": available,
        "discovery_ms": round((perf_counter() - start) * 1000, 2),
        "inference_attempted": False,
        "candidate_validated": None,
    }
    if not available:
        return {**report, "reason": service.unavailable_reason}

    source = "int probe(int sample) { if (sample > 0 { return sample; } return 0; }"
    predictor = MLCorrectionPredictor.load(ROOT / "models" / "syntax_error_classifier.joblib")
    return {**report, **verify_edit(service, predictor, source)}


def verify_edit(service, predictor, source):
    baseline = parse(source)
    diagnostic = baseline.syntax_errors[0]
    context = ErrorContext.from_diagnostic(diagnostic, baseline.tokens, source)
    orchestrator = CorrectionOrchestrator(predictor, llm_fallback=service)
    start = perf_counter()
    result = orchestrator._try_llm_fallback(
        source, baseline, diagnostic, context, predictor.predict_error_type(context), {source}
    )
    return {
        "inference_attempted": result.attempted,
        "model_response_received": result.suggestion is not None or bool(
            result.error and result.error.startswith("Malformed Ollama response:")
        ),
        "inference_and_validation_ms": round((perf_counter() - start) * 1000, 2),
        "candidate_validated": bool(result.accepted and analyze_source_semantics(result.validation.corrected_source).success),
        "safety": assess_repair(result.candidate, result.validation).to_dict(),
        "result": result.to_dict(),
    }


LIVE_CASE_IDS = {
    "v2-loop-accumulator", "v2-control-condition", "v2-array-index-closer",
    "v2-ambiguous-loop-return", "v2-operator-backwards",
}


def verify_benchmark(service):
    start = perf_counter()
    available = service.available
    report = {
        "model": service.model, "available": available,
        "discovery_ms": round((perf_counter() - start) * 1000, 2),
        "live_ollama_status": "NOT_VERIFIED", "cases": [],
    }
    if not available:
        return {**report, "reason": service.unavailable_reason}
    predictor = MLCorrectionPredictor.load(ROOT / "models" / "syntax_error_classifier.joblib")
    for case in load_cases(corpus="holdout"):
        if case["id"] not in LIVE_CASE_IDS:
            continue
        result = verify_edit(service, predictor, case["source"])
        validation = result["result"]["validation"]
        proposed = repair_key(validation["corrected_source"]) if validation and result["candidate_validated"] else None
        accepted = {repair_key(source) for source in case["acceptable_sources"]}
        outcome = (
            "AMBIGUOUS_INTENT" if not case["unambiguous"] else
            "ACCEPTED_REFERENCE" if proposed in accepted else
            "REJECTED_REFERENCE" if proposed in {repair_key(source) for source in case["rejected_sources"]} else
            "UNKNOWN_INTENT"
        )
        report["cases"].append({"id": case["id"], "outcome": outcome, **result})
    rows = report["cases"]
    report["model_responses"] = sum(row["model_response_received"] for row in rows)
    report["valid_candidates"] = sum(row["candidate_validated"] for row in rows)
    report["rejected_responses"] = sum(row["model_response_received"] and not row["candidate_validated"] for row in rows)
    if report["model_responses"]:
        report["live_ollama_status"] = "VERIFIED"
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--benchmark", action="store_true")
    parser.add_argument("--out", type=Path, help="write the benchmark only if a model response arrives")
    args = parser.parse_args()
    if args.out and not args.benchmark:
        parser.error("--out requires --benchmark")
    service = OllamaFallbackService()
    result = verify_benchmark(service) if args.benchmark else verify(service)
    payload = json.dumps(result, indent=2)
    print(payload)
    if args.out and result.get("model_responses"):
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(payload + "\n", encoding="utf-8")
    raise SystemExit(0 if result.get("valid_candidates") or result.get("candidate_validated") else 1)
