"""Protect Phase 1 review decisions and optional Ollama behavior."""

from io import BytesIO
import json
from urllib.error import URLError

import pytest

from ai.correction_orchestrator import CorrectionOrchestrator, CorrectionStatus
from ai.correction_safety import repair_key
from ai.error_predictor import MLCorrectionPredictor
from ai.llm_fallback import OllamaFallbackService
from backend.app import dependencies
from benchmarks.run import MODEL
from scripts.verify_ollama import verify


@pytest.fixture(scope="module")
def orchestrator():
    return CorrectionOrchestrator(MLCorrectionPredictor.load(MODEL))


def test_behavior_changing_semantic_repair_requires_review_even_in_suggestion_mode(orchestrator):
    source = "int archive[3]; void save(int i) { archive(i) = 7; }"
    for auto_apply in (False, True):
        result = orchestrator.correct(source, auto_apply=auto_apply)
        assert result.corrected_source == source and result.corrections_applied == 0
        entry = result.history[0]
        assert entry.status is CorrectionStatus.SUGGESTED
        assert entry.safety.category == "POTENTIALLY_BEHAVIOR_CHANGING"
        assert entry.validation.relevant_valid
        assert "archive[i] = 7" in entry.validation.corrected_source


def test_repair_keys_keep_literal_whitespace_and_distinct_operator_tokens():
    assert repair_key('int x = 7;') == repair_key('int x=7 ;')
    assert repair_key('int x = a++ + b;') != repair_key('int x = a + ++b;')
    assert repair_key('void print() { emit("a  b"); }') != repair_key('void print() { emit("a b"); }')


def test_missing_backend_model_reports_503_and_retains_analysis(monkeypatch):
    from fastapi.testclient import TestClient
    from backend.app.main import app

    dependencies.get_predictor.cache_clear()
    monkeypatch.setattr(dependencies, "MODEL_PATH", MODEL.with_name("missing.joblib"))
    with TestClient(app) as client:
        assert not client.get("/health").json()["ml_model_loaded"]
        assert client.post("/correct", json={"code": "int main() { return 0; }"}).status_code == 503
        assert client.post("/analyze", json={"code": "int main() { return 0; }"}).json()["success"]


def ollama_service(chat_result=None, *, tags=("llama3.2:3b",), connection_error=False):
    def opener(request, timeout):
        if connection_error:
            raise URLError("connection refused")
        if request.full_url.endswith("/api/tags"):
            assert 0 < timeout <= 1.5
            return BytesIO(json.dumps({"models": [{"name": tag} for tag in tags]}).encode())
        assert request.full_url.endswith("/api/chat")
        assert timeout == 0.25
        if isinstance(chat_result, Exception):
            raise chat_result
        parsed = json.loads(request.data)
        assert parsed["model"] == "llama3.2:3b"
        assert parsed["stream"] is False
        if callable(chat_result):
            return BytesIO(json.dumps(chat_result(parsed)).encode())
        return BytesIO(json.dumps(chat_result).encode())

    return OllamaFallbackService(
        host="http://127.0.0.1:11434", model="llama3.2:3b", timeout=0.25, opener=opener,
    )


def test_missing_exact_model_and_unavailable_service():
    assert verify(ollama_service(tags=("llama3.2:1b",)))["inference_attempted"] is False
    assert verify(ollama_service(connection_error=True))["available"] is False


@pytest.mark.parametrize(
    "reply,error",
    [(TimeoutError(), "TimeoutError"), ([], "Malformed Ollama response"),
     ({"message": {"content": "invalid"}}, "Malformed Ollama response"),
     ({"message": {"content": ""}}, "Malformed Ollama response")],
)
def test_ollama_failure_reports_latency_and_leaves_candidate_unapproved(reply, error):
    result = verify(ollama_service(reply))
    assert result["inference_attempted"]
    assert result["inference_and_validation_ms"] >= 0
    assert not result["candidate_validated"]
    assert error in result["result"]["error"]


def test_ollama_structured_suggestion_is_revalidated():
    def generated(request):
        span = "int probe(int sample) { if (sample > 0"
        return {"message": {"content": json.dumps({
            "action": "INSERT", "replacement_text": ")",
            "target_start": len(span), "target_end": len(span),
            "reason": "Close the condition before the body",
        })}}

    result = verify(ollama_service(generated))
    assert result["inference_attempted"] and result["candidate_validated"]
    assert result["result"]["validation"]["valid"]
    assert result["inference_and_validation_ms"] >= 0


def test_invalid_ollama_configuration_disables_optional_service():
    service = OllamaFallbackService(host="file:///tmp/model")
    assert not service.available
    assert "HTTP(S) origin" in service.unavailable_reason


def test_ollama_review_rejects_a_string_instead_of_candidate_ids():
    from ai.error_context import ErrorContext
    from compiler.parser import parse

    source = "int read() { return 7 }"
    parsed = parse(source)
    context = ErrorContext.from_diagnostic(parsed.syntax_errors[0], parsed.tokens, source)
    content = json.dumps({"approved_ids": "A", "scores": {"A": 0.9}})
    service = ollama_service({"message": {"content": content}})
    result = service.review_candidates(source, context, [{"id": "A", "corrected_code": "int read(){ return 7; }"}])
    assert result.attempted
    assert result.approved_ids == ()
    assert "ValueError" in result.error
