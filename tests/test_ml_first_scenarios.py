"""End-to-end regression matrix for the ML-first Mini-C correction pipeline."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from ai.correction_orchestrator import CorrectionOrchestrator
from ai.dataset_generator import CorrectionClass, read_jsonl
from ai.error_predictor import MLCorrectionPredictor
from backend.app.main import app
from compiler.lexer import tokenize
from compiler.parser import parse


@pytest.fixture(scope="module")
def predictor() -> MLCorrectionPredictor:
    return MLCorrectionPredictor.load("models/syntax_error_classifier.joblib")


@pytest.fixture(scope="module")
def orchestrator(predictor: MLCorrectionPredictor) -> CorrectionOrchestrator:
    return CorrectionOrchestrator(predictor)


@pytest.mark.parametrize(
    "name,source,expected",
    [
        (
            "exact screenshot: comma declarations + dot comparison",
            "int main(){ int a,b; if(a.b){return 0;} }",
            "int main(){ int a,b; if(a>b){return 0;} }",
        ),
        (
            "dot before numeric comparison in if",
            "int main(){ int x=3; if(x.5){return 0;} }",
            "int main(){ int x=3; if(x> 5){return 0;} }",
        ),
        (
            "dot before numeric comparison in for header",
            "int main(){ for(i=0;i.5;i++){x=x+1;} }",
            "int main(){ for(i=0;i> 5;i++){x=x+1;} }",
        ),
        (
            "comma used instead of less-than",
            "int main(){ int x=3; if(x,5){return 0;} }",
            "int main(){ int x=3; if(x<5){return 0;} }",
        ),
        (
            "8 typed in place of multiplication",
            "int main(){ int x=3; x 8 8; return 0; }",
            "int main(){ int x=3; x * 8; return 0; }",
        ),
        (
            "plus typed instead of assignment",
            "int main(){ int x + 5; return 0; }",
            "int main(){ int x = 5; return 0; }",
        ),
        (
            "colon typed instead of semicolon",
            "int main(){ int x: return 0; }",
            "int main(){ int x; return 0; }",
        ),
        (
            "9 typed instead of opening parenthesis",
            "int main(){ if 9x > 5) { return 0; } }",
            "int main(){ if (x > 5) { return 0; } }",
        ),
        (
            "missing close parenthesis before body",
            "int main(){ if(x>50 { return 0; } }",
            "int main(){ if(x>50) { return 0; } }",
        ),
        (
            "array declaration open parenthesis typo",
            "int main(){ int arr(5]; return 0; }",
            "int main(){ int arr[5]; return 0; }",
        ),
        (
            "array declaration close parenthesis typo",
            "int main(){ int arr[5); return 0; }",
            "int main(){ int arr[5]; return 0; }",
        ),
        (
            "array index wrong closing delimiter",
            "int main(){ int arr[5]; int i=2; arr(i] = 10; return 0; }",
            "int main(){ int arr[5]; int i=2; arr[i] = 10; return 0; }",
        ),
        (
            "array index wrong opening delimiter",
            "int main(){ int arr[5]; int i=2; arr[i) = 10; return 0; }",
            "int main(){ int arr[5]; int i=2; arr[i] = 10; return 0; }",
        ),
        (
            "array written with function-call delimiters",
            "int main(){ int arr[5]; int i=2; arr(i) = 10; return 0; }",
            "int main(){ int arr[5]; int i=2; arr[i] = 10; return 0; }",
        ),
        (
            "missing semicolon",
            "int main(){ int x=5 return x; }",
            "int main(){ int x=5; return x; }",
        ),
        (
            "missing square bracket",
            "int main(){ int a[5; return 0; }",
            "int main(){ int a[5]; return 0; }",
        ),
        (
            "missing closing brace",
            "int main(){ int x=5; return x;",
            "int main(){ int x=5; return x;}",
        ),
        (
            "misspelled return keyword",
            "int main(){ int x=3; retrun x; }",
            "int main(){ int x=3; return x; }",
        ),
        (
            "comparison operator transposition",
            "int main(){ int x=3; if(x => 2){return 0;} }",
            "int main(){ int x=3; if(x >= 2){return 0;} }",
        ),
        (
            "compound mismatched delimiter repair",
            "int main(){ int x=1; if ((x > 5] { return x; } return 0; }",
            "int main(){ int x=1; if ((x > 5)) { return x; } return 0; }",
        ),
    ],
)
def test_repair_scenario_matrix(orchestrator, name: str, source: str, expected: str) -> None:
    result = orchestrator.correct(source, auto_apply=True)
    assert result.success, f"{name}: correction failed ({result.stop_reason})"
    assert result.corrected_source == expected, f"{name}: got {result.corrected_source!r}"
    assert parse(result.corrected_source).valid, f"{name}: correction did not parse"


def test_exact_screenshot_via_http_correct_endpoint() -> None:
    client = TestClient(app)
    source = "int main(){ int a,b; if(a.b){return 0;} }"
    response = client.post("/correct", json={"code": source})
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["success"] is True
    assert body["corrected_code"] == "int main(){ int a,b; if(a>b){return 0;} }"
    assert body["fully_syntactically_valid"] is True
    assert body["corrections_applied"] == 1


def test_valid_comma_separated_declarations_are_supported() -> None:
    source = "int main(){ int a,b; a=1; b=2; return a+b; }"
    result = parse(source)
    assert result.valid, result.syntax_errors


def test_ambiguous_edit_is_not_silently_applied(orchestrator) -> None:
    # Both assignment and equality interpretations are plausible. Preserve the
    # original rather than silently making an arbitrary semantic choice.
    source = "int main(){ int x=0; x == = 3; return 0; }"
    result = orchestrator.correct(source, auto_apply=True)
    assert result.success is False
    assert result.corrected_source == source
    assert result.stop_reason == "ambiguous_valid_candidates"


def test_dot_outside_condition_is_not_guessed_as_comparison(orchestrator) -> None:
    source = "int main(){ int a=1; int b=2; a.b; return 0; }"
    result = orchestrator.correct(source, auto_apply=True)
    assert result.corrected_source == source
    assert result.success is False


@pytest.mark.parametrize("label", [item.value for item in CorrectionClass if item.value not in {"DECLARATION_DOT_ERROR", "DECLARATION_COLON_ERROR", "SCALAR_ARRAY_USE_ERROR", "ARRAY_BRACE_INDEX_ERROR"}])
def test_each_trained_class_repairs_a_packaged_example(orchestrator, label: str) -> None:
    records = read_jsonl("datasets/syntax_corrections.jsonl")
    record = next(item for item in records if item.label == label)
    result = orchestrator.correct(record.corrupted_source, auto_apply=True)
    assert result.predictions and result.predictions[0].label == label
    # Declaration-separator errors can have multiple equally valid repairs; the
    # interactive UI intentionally does not silently choose one. The options
    # endpoint is responsible for presenting both choices to the user.
    if label == CorrectionClass.DECLARATION_SEPARATOR_ERROR.value:
        assert parse(result.corrected_source).valid
        assert result.stop_reason == "source_is_syntactically_valid"
        return
    assert result.success, f"{label}: {result.stop_reason}"
    assert parse(result.corrected_source).valid
    expected_tokens, expected_errors = tokenize(record.original_source)
    actual_tokens, actual_errors = tokenize(result.corrected_source)
    assert not expected_errors and not actual_errors
    assert [(t.type, t.lexeme) for t in actual_tokens] == [(t.type, t.lexeme) for t in expected_tokens]
