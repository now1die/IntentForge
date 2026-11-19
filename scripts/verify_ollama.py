"""Probe local Ollama and check a real structured edit when the model is reachable."""

import json
from time import perf_counter

from ai.correction_orchestrator import CorrectionOrchestrator
from ai.error_context import ErrorContext
from ai.error_predictor import MLCorrectionPredictor
from ai.llm_fallback import OllamaFallbackService
from benchmarks.corpus import ROOT
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
    baseline = parse(source)
    diagnostic = baseline.syntax_errors[0]
    context = ErrorContext.from_diagnostic(diagnostic, baseline.tokens, source)
    predictor = MLCorrectionPredictor.load(ROOT / "models" / "syntax_error_classifier.joblib")
    orchestrator = CorrectionOrchestrator(predictor, llm_fallback=service)
    start = perf_counter()
    result = orchestrator._try_llm_fallback(
        source, baseline, diagnostic, context, predictor.predict_error_type(context), {source}
    )
    return {
        **report,
        "inference_attempted": result.attempted,
        "inference_and_validation_ms": round((perf_counter() - start) * 1000, 2),
        "candidate_validated": bool(result.accepted and analyze_source_semantics(result.validation.corrected_source).success),
        "result": result.to_dict(),
    }


if __name__ == "__main__":
    result = verify(OllamaFallbackService())
    print(json.dumps(result, indent=2))
    raise SystemExit(0 if result["candidate_validated"] else 1)
