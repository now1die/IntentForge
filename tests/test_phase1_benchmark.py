"""Independent-corpus, reproducibility and intention-scoring regressions."""

import json

from benchmarks.corpus import load_cases, overlapping_cases
from benchmarks.run import audit_source, intention_outcome, run, write_reports


def test_frozen_corpus_is_separate_and_supported_references_validate():
    cases = load_cases()
    assert not overlapping_cases(cases)
    assert {case["corpus"] for case in cases} == {"handwritten", "generated"}
    for case in cases:
        if not case["minic_supported"]:
            continue
        assert audit_source(case["source"])["valid"] == (
            not case["has_error"] or case["detection_scope"] == "logic"
        ), case["id"]
        for reference in case["acceptable_sources"] + case["rejected_sources"]:
            assert audit_source(reference)["valid"], (case["id"], reference)


def test_intention_outcomes_distinguish_known_and_unverified_behavior():
    cases = {case["id"]: case for case in load_cases()}
    case = cases["seed-comparison-spelling"]
    assert intention_outcome(case, case["acceptable_sources"][0], True) == "CORRECT_INTENT_RECOVERY"
    assert intention_outcome(case, case["rejected_sources"][0], True) == "INCORRECT_INTENT_RECOVERY"
    assert intention_outcome(case, None, False) == "UNKNOWN_INTENT"
    assert intention_outcome(case, "bool other() { return false; }", True) == "UNKNOWN_INTENT"
    ambiguous = cases["seed-ambiguous-condition"]
    assert intention_outcome(ambiguous, ambiguous["acceptable_sources"][0], True) == "AMBIGUOUS_INTENT"


def test_benchmark_decisions_reproduce_and_reports_capture_unavailable_modes(tmp_path):
    cases = load_cases()
    first = run(cases, repeats=1, ollama=False)
    second = run(cases, repeats=1, ollama=False)
    assert first["dataset_sha256"] == second["dataset_sha256"]
    for mode in ("rule_based", "existing_ml", "hybrid"):
        left, right = (report["modes"][mode]["cases"] for report in (first, second))
        assert [{k: v for k, v in row.items() if k != "latency_ms"} for row in left] == [
            {k: v for k, v in row.items() if k != "latency_ms"} for row in right
        ]
    hybrid = {row["id"]: row for row in first["modes"]["hybrid"]["cases"]}
    assert hybrid["seed-pointer"]["status"] == "UNSUPPORTED_MINIC"
    logical_error = hybrid["seed-arithmetic"]
    assert logical_error["status"] == "UNSUPPORTED_LOGIC_DETECTION"
    assert not logical_error["detected"] and logical_error["ranked_proposals"] == []
    assert first["modes"]["ollama_assisted"] == {"available": False, "reason": "Skipped by request"}

    write_reports(first, tmp_path)
    assert json.loads((tmp_path / "phase1-v1.json").read_text()) == first
    markdown = (tmp_path / "phase1-v1.md").read_text()
    assert "Top 3" in markdown
    assert "Skipped by request" in markdown


def test_missing_model_keeps_rule_benchmark_available(tmp_path):
    report = run(load_cases()[:2], tmp_path / "missing.joblib", repeats=1, ollama=False)
    assert report["modes"]["rule_based"]["available"]
    assert report["modes"]["existing_ml"]["reason"] == "Classifier unavailable (FileNotFoundError)"
    assert report["modes"]["hybrid"]["available"] is False
