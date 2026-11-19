"""Replay the frozen Phase 5 research cohort with static and optional isolated observations."""

import argparse
from collections import Counter
from copy import copy
from difflib import SequenceMatcher
from hashlib import sha256
from itertools import combinations
import json
from math import sqrt
from pathlib import Path
from time import perf_counter

from ai.behavior_oracle import ExecutionLimits, Status, Vector
from ai.correction_safety import repair_key
from ai.intention_context import Requirement
from ai.intention_engine import analyze_intention, order_candidates
from ai.intention_phase5 import evidence_order
from ai.intention_v3_ranker import load_generalized_ranker
from compiler.lexer import tokenize
from vm.behavioral_executor import MiniCOracle

ROOT = Path(__file__).parent
DATA = ROOT / "data/phase5-v1.json"
FROZEN = "a27b4bae2284354f98567b7041deb32da6d1202a44e8ae75519479ad3dc90500"
PARTITIONS = {"training", "selection", "calibration", "development", "final"}
# The pre-evaluation leakage audit quarantined these development-side records.
# No final input, reference or vector was changed.
QUARANTINE = {"diameter-transform": "gate-pick", "arc-precision": "quality-samples"}
URL = "/v1/behavioral-verification"


def shape(source):
    names = {}
    return tuple((token.type, names.setdefault(token.lexeme, len(names)) if token.type == "IDENTIFIER" else token.lexeme)
                 for token in tokenize(source)[0])


def historical_sources(value):
    if isinstance(value, dict):
        for key, child in value.items():
            if key in {"source", "code", "broken", "broken_code", "fixed", "fixed_code", "reference"}:
                if isinstance(child, str) and "{" in child:
                    yield child
            yield from historical_sources(child)
    elif isinstance(value, list):
        for child in value:
            yield from historical_sources(child)


def load_audited():
    raw = DATA.read_bytes()
    assert sha256(raw).hexdigest() == FROZEN, "Frozen Phase 5 data changed."
    recorded = json.loads(raw)["families"]
    assert len({case["family"] for case in recorded}) == len(recorded)
    by_family = {case["family"]: case for case in recorded}
    for held_out, duplicate in QUARANTINE.items():
        assert by_family[held_out]["partition"] != "final" and by_family[duplicate]["partition"] == "final"
        assert shape(by_family[held_out]["source"]) == shape(by_family[duplicate]["source"])
    rows = [row for row in recorded if row["family"] not in QUARANTINE]
    assert {case["partition"] for case in rows} == PARTITIONS
    past_keys = set()
    for path in sorted(DATA.parent.glob("*.json")):
        if path != DATA:
            past_keys.update(repair_key(source) for source in historical_sources(json.loads(path.read_text())))
    assert not any(repair_key(row["source"]) in past_keys for row in rows)
    structures = {row["family"]: shape(row["source"]) for row in rows}
    near = []
    outputs = []
    oracles = {row["family"]: tuple((tuple(item["arguments"]), item["expected"]) for item in row["vectors"]) for row in rows}
    for a, b in combinations(rows, 2):
        if a["partition"] == b["partition"]:
            continue
        left, right = a["family"], b["family"]
        assert structures[left] != structures[right], (left, right)
        assert a["specification"] != b["specification"]
        ratio = SequenceMatcher(None, structures[left], structures[right], autojunk=False).ratio()
        if ratio >= .88:
            near.append({"families": [left, right], "token_similarity": round(ratio, 3)})
        if oracles[left] == oracles[right]:
            outputs.append([left, right])
    repeated_categories = {key: sorted({row["partition"] for row in rows if row["category"] == key})
                           for key, count in Counter(row["category"] for row in rows).items() if count > 1}
    return rows, {"sha256": FROZEN, "partitions": dict(sorted(Counter(row["partition"] for row in rows).items())),
                  "near_token_pairs": near, "reused_full_vectors": outputs, "repeated_categories": repeated_categories,
                  "historical_sources_checked": len(past_keys), "quarantined_before_evaluation": QUARANTINE}


def reference_rank(case, candidates):
    refs = {repair_key(source) for source in case["references"]}
    return next((index for index, source in enumerate(candidates, 1) if repair_key(source) in refs), None)


def static_row(case, result, ordered=None):
    candidates = result.candidates if ordered is None else ordered
    return {"family": case["family"], "repair_rank": reference_rank(case, [item.proposed_code for item in candidates]),
            "proposals": len(candidates), "valid": sum(item.compiler_valid for item in candidates),
            "alert": result.finding in {"COMPILER_ERROR", "HEURISTIC_SUSPICION", "SPECIFICATION_SUPPORTED_SUSPICION"},
            "structural_alert": bool(result.structural_scan and result.structural_scan["findings"]),
            "located_evidence": bool(result.evidence) and all(fact.span is not None for fact in result.evidence),
            "scored_candidates": sum(item.relative_score is not None for item in candidates),
            "abstained": not candidates or candidates[0].to_dict(case["source"], result.decision == "AMBIGUOUS", True)["recommendation"] == "ABSTAIN",
            "attempts": result.attempts}


def fraction(k, n):
    if not n:
        return {"hits": k, "total": n, "wilson95": None}
    p = k / n
    z = 1.96
    mid = (p + z*z/(2*n)) / (1+z*z/n)
    half = z * sqrt(p*(1-p)/n + z*z/(4*n*n)) / (1+z*z/n)
    return {"hits": k, "total": n, "wilson95": [round(max(0, mid-half), 3), round(min(1, mid+half), 3)]}


def summarize(cases, outcomes, *, detection="alert"):
    matched = [(case, row) for case, row in zip(cases, outcomes, strict=True)]
    positives = [(case, row) for case, row in matched if case["references"]]
    controls = [row for case, row in matched if case["control"]]
    hits = sum(row[detection] for _, row in positives)
    false = sum(row[detection] for row in controls)
    candidates = sum(row["proposals"] for _, row in matched)
    categories = sorted({case["category"] for case, _ in positives})
    return {"detection_recall": fraction(hits, len(positives)), "precision": fraction(hits, hits+false),
            "false_positive_rate": fraction(false, len(controls)), "control_abstention": fraction(sum(row["abstained"] for row in controls), len(controls)),
            "per_category_detection": {key: fraction(sum(row[detection] for case, row in positives if case["category"] == key),
                                                     sum(case["category"] == key for case, _ in positives)) for key in categories},
            "evidence_completeness": fraction(sum(row[detection] and row["located_evidence"] for case, row in matched),
                                             sum(row[detection] for case, row in matched)),
            "candidate_recall": fraction(sum(row["repair_rank"] is not None for _, row in positives), len(positives)),
            "top_1": fraction(sum(row["repair_rank"] == 1 for _, row in positives), len(positives)),
            "top_3": fraction(sum(row["repair_rank"] is not None and row["repair_rank"] <= 3
                                  for _, row in positives), len(positives)),
            "compiler_validity": fraction(sum(row["valid"] for _, row in matched), candidates),
            "abstention": fraction(sum(row["abstained"] for _, row in matched), len(matched)),
            "incorrect_recommendations": sum(not row["abstained"] and row["repair_rank"] != 1
                                             for case, row in matched if case["control"] or case["references"])}


def measure_static(cases, ranker):
    configurations = {key: [] for key in ("v4_baseline", "structural_scan_only", "generation_deterministic",
                                           "same_pool_v4", "same_pool_v4_pairwise", "same_pool_structural_features")}
    times = []
    for case in cases:
        source = case["source"]
        baseline = analyze_intention(source, phase35=True, expanded_ranker=ranker)
        scan = analyze_intention(source, phase5=True, phase5_generate=False, expanded_ranker=ranker)
        started = perf_counter()
        new = analyze_intention(source, phase5=True)
        times.append((perf_counter() - started) * 1000)
        assert new.context.compiler_valid == case["compiler_valid"], case["family"]
        oracle = MiniCOracle()
        vectors = tuple(Vector.model_validate(vector) for vector in case["vectors"])
        for reference in case["references"]:
            assert oracle.verify(reference, case["entry"], vectors, ExecutionLimits()).status == Status.MATCHES_SUPPLIED_TESTS, case["family"]
        for key, result in (("v4_baseline", baseline), ("structural_scan_only", scan), ("generation_deterministic", new)):
            configurations[key].append(static_row(case, result))
        for key, method in (("same_pool_v4", None), ("same_pool_v4_pairwise", "pairwise")):
            ordered = order_candidates([copy(item) for item in new.candidates], None,
                                       generalized=True, expanded=ranker, experimental=method)
            configurations[key].append(static_row(case, new, ordered))
        configurations["same_pool_structural_features"].append(static_row(case, new, evidence_order(new.candidates)))
    return {key: {"metrics": summarize(cases, rows), "cases": rows} for key, rows in configurations.items()}, times


def guided(cases, mode):
    rows = []
    controls = []
    for case in cases:
        text = case[mode]
        if text is None:
            continue
        requirement = (Requirement(function=case["entry"], description=text, return_ordinal=case.get("return_ordinal"))
                       if mode == "natural" else
                       Requirement(function=case["entry"], return_expression=text, return_ordinal=case.get("return_ordinal")))
        rows.append(static_row(case, analyze_intention(case["source"], requirement, phase5=True)))
        controls.append(case)
    return {"metrics": summarize(controls, rows), "cases": rows}


def latency(values):
    ordered = sorted(values)
    return {"mean_ms": round(sum(values)/len(values), 3), "median_ms": round((ordered[(len(values)-1)//2] + ordered[len(values)//2])/2, 3),
            "p95_ms": round(ordered[(95*len(values)+99)//100-1], 3)}


def measure_probe_ablation():
    from execution_service.contracts import LocalLimits
    from execution_service.probes import comparable_outcome, compare_probes, ranked_probes
    from vm.interpreter import prepare
    from vm.runtime import WorkBudget

    identity = "int f(int x){return x;}"
    cases = {
        "reversed_threshold": (identity, "int f(int x){if(15==x){return x+1;}return x;}"),
        "runtime_at_boundary": (identity, "int f(int x){if(x==9){return x/(x-x);}return x;}"),
        "paired_inputs": ("int f(int x,int y){return x;}", "int f(int x,int y){return x+x*y;}"),
        "equivalent": (identity, "int f(int x){return 0+x;}"),
    }
    result = {}
    for family, sources in cases.items():
        pool = [(f"IR-{index:012x}", prepare(source)) for index, source in enumerate(sources)]
        result[family] = {}
        for label, method in (("legacy", compare_probes), ("phase5", ranked_probes)):
            budget = WorkBudget(200_000)
            probes = method(pool, "f", (), LocalLimits(), budget)
            distinguish = []
            for index, probe in enumerate(probes, 1):
                left, right = map(comparable_outcome, probe.candidates)
                if left is not None and right is not None and left != right:
                    distinguish.append(index)
            result[family][label] = {"probes": len(probes), "pair_distinguished": bool(distinguish),
                                     "first_distinguishing_position": next(iter(distinguish), None),
                                     "steps": 200_000 - budget.remaining}
    return result


def measure_live(cases):
    from fastapi.testclient import TestClient
    from backend.app.main import app

    records = []
    elapsed = []
    with TestClient(app, base_url="http://127.0.0.1:8000", client=("127.0.0.1", 49000)) as local:
        assert local.get(URL + "/capability").json()["status"] == "available"
        for case in cases:
            payload = {"engine_version": 5, "compare_candidates": True, "source": case["source"],
                       "entry_point": case["entry"], "vectors": case["vectors"]}
            started = perf_counter()
            reply = local.post(URL, json=payload).json()
            elapsed.append((perf_counter()-started)*1000)
            assert reply["availability"]["status"] == "available", reply
            assert reply["requires_approval"]
            candidates = {item["id"]: item for item in reply["candidates"]}
            probes = reply["probes"]
            records.append({"family": case["family"], "static_rank": reference_rank(case, [row["source"] for row in candidates.values()]),
                            "behavior_rank": reference_rank(case, [candidates[key]["source"] for key in reply["review_order"]]),
                            "original_status": reply["original"]["status"], "candidate_statuses": [row["behavior"]["status"] for row in candidates.values()],
                            "comparison": reply["comparison_status"], "probes": len(probes),
                            "pairs_distinguished": sum(row["new_pairs"] for row in probes),
                            "probe_steps": sum(row["steps"] for row in probes),
                            "test_steps": sum(sample["steps"] for row in (reply["original"], *(item["behavior"] for item in candidates.values()))
                                              for sample in row["execution"]["samples"])})
            if case["ambiguous"]:
                assert reply["comparison_status"] == "MULTIPLE_MATCHES"
                observation = local.post(URL, json={**payload, "vectors": []}).json()
                assert observation["comparison_status"] is None
                assert observation["review_order"] == [candidate["id"] for candidate in observation["candidates"]]
                assert all("expected" not in probe for probe in observation["probes"])
                distinguishing = next(probe for probe in reply["probes"] if probe["relation"] == "disagree")
                supplied = {"arguments": distinguishing["arguments"], "expected": distinguishing["arguments"][0]}
                resolved = local.post(URL, json={**payload, "vectors": [*case["vectors"], supplied]}).json()
                assert resolved["comparison_status"] == "ONE_MATCH"
                records[-1]["additional_explicit_specification"] = "Return the first argument"
                records[-1]["after_new_vector"] = resolved["comparison_status"]
        remote = TestClient(app, client=("198.51.100.3", 49000))
        assert remote.get(URL + "/capability").json()["status"] == "disabled"
    adjudicable = [row for case, row in zip(cases, records, strict=True) if case["references"]]
    stats = {kind: {"top_1": fraction(sum(row[kind] == 1 for row in adjudicable), len(adjudicable)),
                    "top_3": fraction(sum(row[kind] is not None and row[kind] <= 3 for row in adjudicable), len(adjudicable))}
             for kind in ("static_rank", "behavior_rank")}
    stats["original_statuses"] = dict(sorted(Counter(row["original_status"] for row in records).items()))
    stats["candidate_statuses"] = dict(sorted(Counter(status for row in records for status in row["candidate_statuses"]).items()))
    stats["comparison_statuses"] = dict(sorted(Counter(row["comparison"] for row in records).items()))
    supported = sum(status not in {"EXECUTION_UNSUPPORTED", "ORACLE_UNAVAILABLE"} for row in records
                    for status in [row["original_status"], *row["candidate_statuses"]])
    stats["execution_support"] = fraction(supported, len(records) + sum(len(row["candidate_statuses"]) for row in records))
    stats["worker_steps"] = sum(row["test_steps"] + row["probe_steps"] for row in records)
    return {"cases": records, "metrics": stats, "latency": latency(elapsed)}


def evaluate(live=False):
    rows, audit = load_audited()
    ranker, state = load_generalized_ranker(4)
    assert ranker is not None, state
    final = [row for row in rows if row["partition"] == "final"]
    selection = [row for row in rows if row["partition"] == "selection"]
    controls = [row for row in rows if row["partition"] in {"development", "calibration"}]
    selection_results, _ = measure_static(selection, ranker)
    diagnostics, _ = measure_static(controls, ranker)
    final_results, elapsed = measure_static(final, ranker)
    structural = final_results["structural_scan_only"]["cases"]
    report = {"version": 1, "audit": audit, "v4_artifact": state,
              "selection": selection_results, "development_calibration": diagnostics,
              "final": final_results, "latency": latency(elapsed),
              "structural_detector": summarize(final, structural, detection="structural_alert"),
              "natural_language": guided(final, "natural"), "explicit": guided(final, "explicit"),
              "probe_ablation": measure_probe_ablation()}
    if live:
        report["live"] = measure_live(final)
    return report


def stable(report):
    return {key: value for key, value in report.items() if key not in {"latency", "live"}}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--live", action="store_true")
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    result = evaluate(args.live)
    if args.check:
        historical = json.loads((ROOT / "reports/phase5-static-v1.json").read_text())
        assert stable(result) == stable(historical), "Phase 5 reproducible decisions changed."
        if args.live:
            live = json.loads((ROOT / "reports/phase5-live-v1.json").read_text())
            assert {key: value for key, value in result["live"].items() if key != "latency"} == {
                key: value for key, value in live.items() if key != "latency"
            }, "Phase 5 isolated decisions changed."
        print(f"Verified {result['audit']['partitions']['final']} Phase 5 final families.")
    else:
        print(json.dumps(result, indent=2))
