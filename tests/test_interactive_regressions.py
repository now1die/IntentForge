from fastapi.testclient import TestClient

from backend.app.main import app

client = TestClient(app)


def test_declaration_separator_shows_two_distinct_valid_options():
    response = client.post('/correction-options', json={'code': 'int x;y;'})
    assert response.status_code == 200
    data = response.json()
    assert data['prediction']['label'] == 'DECLARATION_SEPARATOR_ERROR'
    codes = [item['corrected_code'] for item in data['options']]
    assert 'int x,y;' in codes
    assert 'int x; int y;' in codes
    assert len(codes) == 2
    assert all(item['fully_valid'] for item in data['options'])


def test_top_level_keyboard_comparison_still_shows_local_repair():
    response = client.post('/correction-options', json={'code': 'if(a.b){return 0;}'})
    assert response.status_code == 200
    data = response.json()
    assert data['prediction']['label'] == 'KEYBOARD_GREATER_THAN'
    assert any(item['corrected_code'] == 'if(a>b){return 0;}' for item in data['options'])
    assert data['options'][0]['fully_valid'] is False


def test_array_call_semantic_error_shows_indexing_option():
    source = 'int main(){ int arr[5]; int i=2; arr(i) = 10; return 0; }'
    response = client.post('/correction-options', json={'code': source})
    assert response.status_code == 200
    data = response.json()
    assert data['prediction']['label'] == 'ARRAY_CALL_ERROR'
    assert any('arr[i]' in item['corrected_code'] for item in data['options'])
    assert data['options'][0]['fully_valid'] is True


def test_selected_correction_validation_endpoint():
    response = client.post('/validate-correction', json={
        'original_code': 'int x;y;',
        'corrected_code': 'int x; int y;',
    })
    assert response.status_code == 200
    assert response.json()['valid'] is True
