"""Classify recorded code-only failures without changing historical judgments."""

import argparse
import json
from pathlib import Path

REPORTS = Path(__file__).with_name("reports")


def historical_taxonomy():
    def read(name):
        return json.loads((REPORTS / f"{name}-v1.json").read_text())

    cohorts = {
        "v2": read("phase2-evaluation")["cohorts"]["final"]["modes"]["context_learned"]["cases"],
        "v2.5": read("phase25-evaluation")["cohorts"]["evaluation"]["configurations"]["full_code_only"]["cases"],
        "v3": read("ml-v3-evaluation")["full_pipeline"]["code_only"]["cases"],
        "v4_external": read("phase35-evaluation")["external"]["v4_deployed"]["cases"],
        "v4": read("phase35-evaluation")["configurations"]["v4_deployed"]["cases"],
    }
    rows = []
    for cohort, cases in cohorts.items():
        for case in cases:
            rank = case.get("first_match_rank")
            hit = case.get("candidate_hit", rank is not None)
            first = case.get("top_1", rank == 1)
            if case["ambiguous"]:
                observed = "ambiguous_intent"
            elif case["finding"] == "UNSUPPORTED_LANGUAGE":
                observed = "unsupported_construct"
            elif not case["known"]:
                continue
            elif not hit:
                observed = "missing_relevant_candidate"
            elif not first:
                observed = "incorrect_ranking"
            else:
                continue
            rows.append({"cohort": cohort, "case": case["id"], "family": case.get("family", case["id"]),
                         "recorded_category": case["category"], "observation": observed,
                         "reason_to_investigate": reasoning_area(case["category"]),
                         "compiler_valid_input": not case.get("compile_fault", case.get("detected_compiler_fault")),
                         "recorded_reference_rank": rank, "recorded_candidate_hit": hit})
    for case in read("phase45-isolation")["repair_families"]:
        if case["runtime_failure"] or case["multiple_matches"] or not case["executable_candidates"]:
            rows.append({"cohort": "phase4.5", "case": case["family"], "family": case["family"],
                         "observation": "ambiguous_intent" if case["multiple_matches"] else
                         "unsupported_construct" if case["original_status"] == "EXECUTION_UNSUPPORTED" else
                         "runtime_failure" if case["runtime_failure"] else "abstained",
                         "recorded_reference_rank": case["reference_static_rank"]})
    return {"version": 1, "rows": rows}


def reasoning_area(category):
    category = category.lower()
    for labels, area in (
        (("boundary", "index", "off_by"), "boundary_reasoning"),
        (("multi", "compound"), "multi_location_consistency"),
        (("argument", "call"), "function_context"),
        (("variable", "identifier", "scope"), "variable_selection"),
        (("operator", "arithmetic", "comparison"), "operator_selection"),
        (("loop", "condition", "branch"), "control_flow"),
        (("return", "assignment", "dependency"), "dataflow"),
    ):
        if any(label in category for label in labels):
            return area
    return "repair_structure_or_context"


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    report = historical_taxonomy()
    if args.check:
        assert report == json.loads((REPORTS / "phase5-failure-taxonomy-v1.json").read_text())
        print(f"Verified {len(report['rows'])} recorded historical observations.")
    else:
        print(json.dumps(report, indent=2))
