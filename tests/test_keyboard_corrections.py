from __future__ import annotations

from ai.correction_orchestrator import CorrectionOrchestrator
from ai.error_predictor import MLCorrectionPredictor


def run(source: str):
    predictor = MLCorrectionPredictor.load("models/syntax_error_classifier.joblib")
    return CorrectionOrchestrator(predictor).correct(source, preview=True)


def test_array_declaration_wrong_opening_bracket_is_ml_fixed():
    result = run("int main(){ int arr(5]; return 0; }")
    assert result.success
    assert result.predictions[0].label == "ARRAY_DECLARATION_ERROR"
    assert "int arr[5];" in result.corrected_source


def test_array_index_wrong_closing_bracket_is_ml_fixed():
    result = run("int main(){ int arr[5]; arr[i) = 10; return 0; }")
    assert result.success
    assert result.predictions[0].label == "ARRAY_INDEX_ERROR"
    assert "arr[i] = 10;" in result.corrected_source


def test_array_call_like_index_is_ml_fixed():
    result = run("int main(){ int arr[5]; arr(i] = 10; return 0; }")
    assert result.success
    assert result.predictions[0].label == "ARRAY_INDEX_ERROR"
    assert "arr[i] = 10;" in result.corrected_source


def test_greater_than_dot_keyboard_slip_is_ml_fixed():
    result = run("int main(){ if(x.5){return 0;} }")
    assert result.success
    assert result.predictions[0].label == "KEYBOARD_GREATER_THAN"
    assert "x> 5" in result.corrected_source


def test_less_than_comma_keyboard_slip_is_ml_fixed():
    result = run("int main(){ if(x,5){return 0;} }")
    assert result.success
    assert result.predictions[0].label == "KEYBOARD_LESS_THAN"
    assert "x<5" in result.corrected_source


def test_plus_equals_keyboard_slip_is_ml_fixed():
    result = run("int main(){ int x + 5; return 0; }")
    assert result.success
    assert result.predictions[0].label == "KEYBOARD_ASSIGNMENT"
    assert "int x = 5;" in result.corrected_source


def test_colon_semicolon_keyboard_slip_is_ml_fixed():
    result = run("int main(){ int x: return 0; }")
    assert result.success
    assert result.predictions[0].label == "KEYBOARD_SEMICOLON"
    assert "int x;" in result.corrected_source


def test_shift_number_open_paren_slip_is_ml_fixed():
    result = run("int main(){ if 9x > 5) { return 0; } }")
    assert result.success
    assert result.predictions[0].label == "KEYBOARD_LPAREN"
    assert "if (x > 5)" in result.corrected_source
