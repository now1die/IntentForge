"""Audit frozen benchmark data, reference validity and holdout separation."""

import json
from collections import Counter

from ai.correction_safety import repair_key
from .behavior import BehaviorSpec
from .corpus import DATA, load_cases, near_duplicate_pairs, overlapping_cases, template_key
from .run import audit_source


def review(cases):
    issues = []
    holdout = [case for case in cases if case["id"].startswith("v2-")]
    earlier = [case for case in cases if not case["id"].startswith("v2-")]
    archived_overlap = overlapping_cases(cases)
    if archived_overlap:
        issues.append(f"Archived training overlap: {', '.join(archived_overlap)}")
    earlier_keys = {template_key(src) for case in earlier for src in [case["source"], *case["acceptable_sources"]]}
    normalized_inputs = {}
    for case in cases:
        label = case["id"]
        source = case["source"]
        accepted, rejected = case["acceptable_sources"], case["rejected_sources"]
        if type(case["has_error"]) is not bool or type(case["minic_supported"]) is not bool or type(case["unambiguous"]) is not bool:
            issues.append(f"{label}: flags must be Boolean")
        if case["detection_scope"] not in {"compiler", "logic", "unsupported"}:
            issues.append(f"{label}: invalid detection scope")
        if not isinstance(source, str) or not source.strip() or not case["category"] or not case["mutation_family"]:
            issues.append(f"{label}: missing content")
        if not all(isinstance(values, list) and all(isinstance(value, str) and value for value in values)
                   for values in (accepted, rejected)):
            issues.append(f"{label}: invalid references")
            continue
        key = template_key(source)
        previous = normalized_inputs.setdefault(key, label)
        if previous != label and case in holdout:
            issues.append(f"{label}: normalized input matches {previous}")
        if case in holdout:
            if (case["provenance"] != "AI_ASSISTED_REVIEWED"
                    or case["review_status"] != "COMPILER_CHECKED_SPEC_REVIEWED"
                    or case["split"] != "phase_1_5_holdout"
                    or (case["intended_source"] is not None and case["intended_source"] not in accepted)):
                issues.append(f"{label}: invalid provenance, split, or intended source")
            if any(template_key(src) in earlier_keys for src in [source, *accepted]):
                issues.append(f"{label}: normalized overlap with historical evaluation")
        supported = case["minic_supported"]
        expected_valid = supported and (not case["has_error"] or case["detection_scope"] == "logic")
        if audit_source(source)["valid"] != expected_valid:
            issues.append(f"{label}: source contradicts the declared compiler validity")
        if {repair_key(src) for src in accepted} & {repair_key(src) for src in rejected}:
            issues.append(f"{label}: conflicting accepted and rejected references")
        for src in [*accepted, *rejected]:
            if not audit_source(src)["valid"]:
                issues.append(f"{label}: invalid reference {src!r}")
        if case.get("behavior") is not None:
            BehaviorSpec.from_dict(case["behavior"])

    pairs = [pair for pair in near_duplicate_pairs(cases) if pair[0].startswith("v2-") or pair[1].startswith("v2-")]
    approved = json.loads((DATA / "reviewed-similarities-v2.json").read_text(encoding="utf-8"))
    actual = {f"{left}|{right}" for left, right, _ in pairs}
    if actual != set(approved):
        issues.extend(f"Unreviewed near duplicate: {pair}" for pair in sorted(actual - set(approved)))
        issues.extend(f"Stale similarity review: {pair}" for pair in sorted(set(approved) - actual))
    return {
        "cases": len(cases), "provenance": Counter(case["provenance"] for case in cases),
        "splits": Counter(case["split"] for case in cases), "near_duplicates": pairs, "errors": issues,
    }


if __name__ == "__main__":
    result = review(load_cases(corpus="all"))
    print(json.dumps(result, indent=2))
    raise SystemExit(bool(result["errors"]))
