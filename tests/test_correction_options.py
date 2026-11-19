from fastapi.testclient import TestClient

from backend.app.main import app


client = TestClient(app)


def test_options_return_multiple_compiler_valid_declaration_choices():
    source = "int main(){ int x;y }"
    response = client.post("/correction-options", json={"code": source})
    assert response.status_code == 200
    data = response.json()
    valid = [item for item in data["options"] if item["fully_valid"]]
    assert len(valid) >= 2
    codes = {item["corrected_code"] for item in valid}
    assert any("int x, y" in code for code in codes)
    assert any("int x; int y" in code for code in codes)


def test_options_fix_keyboard_error_from_screenshot():
    source = "int main(){ int a,b; if(a.b){return 0;} }"
    response = client.post("/correction-options", json={"code": source})
    assert response.status_code == 200
    data = response.json()
    assert data["prediction"]["label"] == "KEYBOARD_GREATER_THAN"
    assert any("if(a>b)" in item["corrected_code"] for item in data["options"])


def test_validate_custom_correction():
    response = client.post(
        "/validate-correction",
        json={
            "original_code": "int main(){ int x;y }",
            "corrected_code": "int main(){ int x, y; }",
        },
    )
    assert response.status_code == 200
    assert response.json()["valid"] is True
