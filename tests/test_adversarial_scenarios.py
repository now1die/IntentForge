from ai.correction_options import suggest_correction_options
from ai.error_predictor import MLCorrectionPredictor

PREDICTOR = MLCorrectionPredictor.load('models/syntax_error_classifier.joblib')


def _options(source):
    result = suggest_correction_options(source, PREDICTOR)
    assert result['success']
    return result


def test_scalar_array_mismatch_is_classified_and_repaired():
    result = _options('int main(){ int arr; arr{5]=10; return 0; }')
    assert result['prediction']['label'] == 'SCALAR_ARRAY_USE_ERROR'
    assert any(o['fully_valid'] and 'int arr[6];' in o['corrected_code'] and 'arr[5]' in o['corrected_code'] for o in result['options'])


def test_array_brace_index_is_repaired():
    result = _options('int main(){ int arr[6]; arr{5]=10; return 0; }')
    assert result['prediction']['label'] == 'ARRAY_BRACE_INDEX_ERROR'
    assert any(o['fully_valid'] and 'arr[5]=10' in o['corrected_code'] for o in result['options'])


def test_declaration_dot_has_multiple_valid_options():
    result = _options('int main(){ int a.b; return 0; }')
    assert result['prediction']['label'] == 'DECLARATION_DOT_ERROR'
    valid = [o for o in result['options'] if o['fully_valid']]
    assert len(valid) >= 2
    assert any('int a, b;' in o['corrected_code'] for o in valid)
    assert any('int a;\nint b;' in o['corrected_code'] for o in valid)


def test_declaration_separator_has_multiple_valid_options():
    result = _options('int main(){ int x;y; return 0; }')
    valid = [o for o in result['options'] if o['fully_valid']]
    assert len(valid) >= 2
    assert any('int x, y;' in o['corrected_code'] for o in valid)
    assert any('int x; int y;' in o['corrected_code'] for o in valid)
