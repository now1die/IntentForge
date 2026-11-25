import json
from pathlib import Path

from ai.intention_context import Example
from ai.intention_engine import analyze_intention
from backend.app.main import app
from fastapi.testclient import TestClient

ARCHIVE = Path(__file__).resolve().parents[1] / "benchmarks/phase115_data/cases-v1.json"
FLAG = ("int f(bool assign, int input){int data=-1;bool present=false;"
        "if(assign){data=input;present=true;}if(data==-1){return 9;}return data;}")
GRID = ("int f(int row,int col,int a,int b){int cells[6];"
        "cells[0]=a;cells[1]=b;cells[2]=2;cells[3]=3;cells[4]=4;cells[5]=5;"
        "if(row<0 || row>=2){return -1;}return cells[row*3+col];}")


def examples(pairs):
    return tuple(Example(args, expected) for args, expected in pairs)


def analyze(source, samples=()):
    return analyze_intention(source, phase12=True, phase6_entry="f", phase6_examples=samples)


def report(result):
    return result.program_analysis["phase12"]


def candidate(result, category):
    return next(choice for choice in result.candidates if choice.proposal.category == category)


def test_cfg_join_and_shadowed_cells():
    result = analyze("int f(bool ok){int x;int slots[2]; slots[0]=0; "
                     "if(ok){x=7; {int x=12; return x;}} return slots[0]+slots[1]+x;}")
    facts = [row for row in report(result)["facts"] if row["kind"] == "initialization"]
    assert {row["initialization"] for row in facts if row["name"] == "x"} == {"INITIALIZED", "UNINITIALIZED"}
    assert len({row["binding"] for row in facts if row["name"] == "x"}) == 2
    assert {(row["cell"], row["initialization"]) for row in facts if row["name"] == "slots"} == {
        (0, "INITIALIZED"), (1, "UNINITIALIZED")}
    helper = analyze_intention("int helper(int x){return x+1;}int f(int v){int result=helper(v);return result;}", phase12=True)
    helper_facts = [row for row in report(helper)["facts"] if row["kind"] == "initialization"]
    assert all(row["name"] != "helper" for row in helper_facts)
    assert any(row["name"] == "result" and row["initialization"] == "INITIALIZED" for row in helper_facts)
    joined = analyze("int f(bool ok){int x;if(ok){x=7;}return x;}")
    assert any(row["initialization"] == "MAYBE_INITIALIZED" and row["name"] == "x"
               for row in report(joined)["facts"])


def test_initialized_value_and_presence_are_independent():
    samples = examples([((True, -1), -1), ((False, -1), 9), ((True, 0), 0)])
    result = analyze(FLAG, samples)
    sentinel = next(row for row in report(result)["facts"] if row["kind"] == "sentinel")
    assert (sentinel["initialization"], sentinel["presence"], sentinel["collision"]) == ("INITIALIZED", "UNKNOWN", "POSSIBLE")
    assert "if(!present)" in candidate(result, "SENTINEL_PRESENCE_CONSTRAINT").proposed_code
    assert not analyze(FLAG.replace("data==-1", "!present"), samples).candidates
    assert not analyze(FLAG.replace("present=true", "present=false"), samples).candidates


def test_independent_signed_coordinates_and_rectangular_extent():
    rows = examples([((0, -1, 40, 41), -1), ((0, 3, 40, 41), -1), ((0, 0, 40, 41), 40)])
    result = analyze(GRID, rows)
    facts = [row for row in report(result)["facts"] if row["kind"] == "coordinate"]
    assert {(row["axis"], row["upper_exclusive"], row["validity"]) for row in facts} == {
        ("row", 2, "VALID"), ("column", 3, "UNKNOWN")}
    repaired = candidate(result, "INDEPENDENT_COORDINATE_CONSTRAINT").proposed_code
    assert "col < 0 || col >= 3" in repaired
    assert not analyze(repaired, rows).candidates
    for incomplete in (rows[:1], ()):
        assert not any(choice.proposal.category == "INDEPENDENT_COORDINATE_CONSTRAINT"
                       for choice in analyze(GRID, incomplete).candidates)


def test_archived_logical_empty_offset_is_withheld():
    original = next(row for row in json.loads(ARCHIVE.read_text()) if row["id"] == "empty-retained-run-fault")
    result = analyze(original["source"], examples([(tuple(v["arguments"]), v["expected"]) for v in original["vectors"]]))
    phase = report(result)
    assert any(row["kind"] == "inactive_read" and row["logical_length"] == 0 and row["physical_extent"] == 4
               for row in phase["facts"])
    assert {item["category"] for item in phase["withheld"]} == {"FIXED_ARRAY_INDEX_CONSTRAINT"}
    assert any("return 0" in choice.proposed_code for choice in result.candidates)
    assert not analyze("int f(int pos){int a[2];a[0]=4;return a[pos];}").candidates


def test_phase12_api_is_opt_in_and_source_bound():
    with TestClient(app) as client:
        arguments = {"code": FLAG, "mode": "examples", "requirement": {"function": "f", "examples": [
            {"args": [True, -1], "expected_return": -1}, {"args": [False, 0], "expected_return": 9},
            {"args": [True, 0], "expected_return": 0}]}}
        response = client.post("/v1/intention-analysis", json=arguments | {"engine_version": 12})
        assert response.status_code == 200, response.text
        payload = response.json()
        assert payload["recommendation"] == "ABSTAIN"
        assert payload["candidates"][0]["requires_approval"]
        assert payload["candidates"][0]["source_snapshot"] == payload["source_fingerprint"]
        previous = client.post("/v1/intention-analysis", json=arguments | {"engine_version": 115}).json()
        assert "phase12" not in previous["program_analysis"]


def test_cells_and_path_facts_remain_separate_after_dynamic_writes():
    source = "int f(int i){int p[3];p[i]=1; p[0]=0; if(i==0){i=1; return p[0]+p[1]+i;} return p[1];}"
    facts = report(analyze(source))["facts"]
    assert any(row["kind"] == "physical_index" and row["cell"] == 0 and row["validity"] == "VALID" for row in facts)
    assert any(row["kind"] == "initialization" and row["cell"] == 0 and row["initialization"] == "INITIALIZED"
               for row in facts)
    assert any(row["kind"] == "initialization" and row["cell"] == 1 and row["initialization"] == "MAYBE_INITIALIZED"
               for row in facts)
    assert any(row["kind"] == "initialization" and row["name"] == "i" and row["value"] == 1 and not row["assumptions"]
               for row in facts)


def test_doctor_distinguishes_successful_frontend_html_from_failed_entry(monkeypatch, capsys):
    from scripts import doctor

    def unavailable_compiler(url, payload=None):
        if url.endswith("/analyze"):
            raise OSError
        return {"status": "disabled" if url.endswith("/capability") else "ok"}

    def missing_asset(url, **options):
        if url.endswith("/"):
            return "text/html", b'<script type="module" src="/assets/entry.js"></script>'
        raise OSError

    monkeypatch.setattr(doctor, "json_response", unavailable_compiler)
    monkeypatch.setattr(doctor, "request", missing_asset)
    monkeypatch.setattr(doctor, "node_status", lambda: ("Node 24", True))
    monkeypatch.setattr(doctor, "dependency_status", lambda: ("installed", True))
    monkeypatch.setattr(doctor.sys, "argv", ["doctor"])
    assert doctor.main() == 1
    output = capsys.readouterr().out
    assert "Backend API reachable" in output
    assert "Mini-C compiler analysis failed" in output
    assert "Frontend HTML reachable" in output
    assert "Frontend entry JavaScript unavailable" in output
    assert "Optional interactive execution analysis-only" in output
