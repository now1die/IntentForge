"""Check the Phase 2 splits without fitting a model or scoring final outcomes."""

from collections import Counter
import json

from compiler.semantic_analyzer import analyze_source_semantics

from .corpus import load_cases, near_duplicate_pairs, template_key, training_sources
from .phase2_data import DEVELOPMENT, FINAL, generate


def references(case):
    accepted = case["accepted"]
    return [accepted] if isinstance(accepted, str) else accepted


def audit(development, final, historical=None, archives=None):
    check_near = archives is None
    historical = load_cases(corpus="all") if historical is None else historical
    archives = training_sources() if archives is None else archives
    cases = [*development, *final]
    issues = []
    if len({case["id"] for case in cases}) != len(cases):
        issues.append("Duplicate case IDs")
    fingerprints = {}
    for case in historical:
        for text in (case["source"], *case["acceptable_sources"]):
            fingerprints[template_key(text)] = "historical"
    for broken, reference, _ in archives:
        for text in (broken, reference):
            fingerprints.setdefault(template_key(text), "archive")
    owners = {}
    for case in cases:
        group = case["split"]
        owner = owners.setdefault(case["family"], group)
        if owner != group:
            issues.append(f"Family {case['family']} crosses splits")
        if group not in {"train", "validation", "final"}:
            issues.append(f"Unexpected split {group}")
        for text in (case["source"], *references(case)):
            previous = fingerprints.setdefault(template_key(text), group)
            if previous != group:
                issues.append(f"{case['id']} overlaps a {previous} template")
        for reference in references(case):
            if not analyze_source_semantics(reference).success:
                issues.append(f"{case['id']} has an invalid reference")
    near = []
    if check_near:
        survey = [*[dict(row, split="historical") for row in historical], *cases]
        splits = {case["id"]: case["split"] for case in survey}
        near = [
            (left, right, similarity)
            for left, right, similarity in near_duplicate_pairs(survey, threshold=.94)
            if splits[left] != "historical" and splits.get(right, "archive") != splits[left]
        ]
        issues.extend(f"Cross-split near duplicate {left} / {right}" for left, right, _ in near)
    return {"cases": Counter(case["split"] for case in cases), "families": Counter(owners.values()),
            "near_duplicate_threshold": .94, "cross_split_near_duplicates": near, "issues": sorted(set(issues))}


if __name__ == "__main__":
    development = json.loads(DEVELOPMENT.read_text())
    result = audit(development["cases"], json.loads(FINAL.read_text())["cases"])
    if development != generate():
        result["issues"].append("Committed development data does not reproduce from the generator")
    print(json.dumps(result, indent=2))
    raise SystemExit(bool(result["issues"]))
