"""Replay the frozen Phase 8.5 ablations and isolated holdout verification."""
import argparse
from collections import Counter
import json
from time import perf_counter, sleep

from ai.behavior_oracle import ExecutionLimits, Status, Vector, program_identity
from ai.correction_safety import repair_key
from ai.intention_engine import analyze_intention
from ai.intention_phase85 import CATEGORIES
from vm.behavioral_executor import MiniCOracle

from .phase5_evaluate import fraction, latency
from .phase55_evaluate import stable
from .phase6_evaluate import REPORTS, URL, row, vectors
from .phase65_evaluate import transform_paths
from .phase7_evaluate import observation, static
from .phase75_audit import audit as audit75
from .phase75_evaluate import live_metrics
from .phase75_fixtures import ROOT as PHASE75_ROOT
from .phase8_fixtures import ROOT as PHASE8_ROOT
from .phase8_evaluate import discovery, heldout_candidate, review_burden, worker_call
from .phase85_audit import audit

CONFIGURATIONS = {
    "phase65": {"phase65": True},
    "phase75": {"phase75": True},
    "phase8": {"phase8": True},
    "branches_only": {"phase85": True, "phase85_components": frozenset({"branches"})},
    "coordinated_only": {"phase85": True, "phase85_components": frozenset({"coordinated"})},
    "loops_only": {"phase85": True, "phase85_components": frozenset({"loops"})},
    "phase85": {"phase85": True},
}


def observed(result):
    return result.status, tuple(item.actual for item in result.observations)


def run_projection(case, *, source=None, entry="f", **settings):
    return analyze_intention(source if source is not None else case["source"],
                             phase6_entry=entry, phase6_examples=discovery(case), **settings)


def reference_suites(oracle, cases):
    faults_with_supplied_agreement = []
    for case in cases:
        suites = [vectors(case)]
        if case["holdout_vectors"]:
            suites.append(tuple(Vector.model_validate(vector) for vector in case["holdout_vectors"]))
        for reference in case["references"] or [case["source"]]:
            for suite in suites:
                # The Mini-C reference cross-checks the separately specified oracle.
                assert oracle.verify(reference, "f", suite, ExecutionLimits()).status == Status.MATCHES_SUPPLIED_TESTS, case["id"]
        if case["disposition"] == "fault":
            original = [oracle.verify(case["source"], "f", suite, ExecutionLimits()).status for suite in suites]
            assert any(status == Status.MISMATCHES_SUPPLIED_TESTS for status in original), case["id"]
            if original[0] == Status.MATCHES_SUPPLIED_TESTS:
                faults_with_supplied_agreement.append(case["id"])
    return faults_with_supplied_agreement


def robustness(oracle, cases):
    counts, changes = Counter(), []
    for case in cases:
        suite = vectors(case)
        original = oracle.verify(case["source"], "f", suite, ExecutionLimits())
        base = run_projection(case, phase85=True)
        signature = sorted(candidate.proposal.category for candidate in base.candidates)
        for transform, source, entry in transform_paths(case["source"]):
            execution = oracle.verify(source, entry, suite, ExecutionLimits())
            assert observed(execution) == observed(original), (case["id"], transform)
            result = run_projection(case, source=source, entry=entry, phase85=True)
            counts[transform] += 1
            varied = sorted(candidate.proposal.category for candidate in result.candidates)
            if signature != varied:
                changes.append({"id":case["id"], "transform":transform, "original":signature, "transformed":varied})
            for candidate in result.to_dict()["candidates"]:
                for edit in candidate["edits"]:
                    lower, upper = (edit["span"][position]["offset"] for position in ("start", "end"))
                    assert source[lower:upper] == edit["original"]
    return {"checks": dict(counts), "total": sum(counts.values()), "changes": changes}


def diagnostic(case):
    before, after = [run_projection(case, **settings) for settings in ({"phase8":True}, {"phase85":True})]
    return row(case, after, after.candidates) | {
        "phase8_rank": row(case,before,before.candidates)["rank"],
        "mode": after.program_analysis["phase85"].get("mode"),
        "status": after.program_analysis["phase85"]["status"],
    }


def mechanisms(oracle, cases):
    details, generated, discovery_passes, examined_sizes, shape_counts = [], 0, 0, Counter(), Counter()
    times = []
    for case in cases:
        start = perf_counter()
        result = run_projection(case, phase85=True)
        times.append(1000 * (perf_counter() - start))
        report = result.program_analysis["phase85"]
        candidates = [choice for choice in result.candidates if choice.proposal.category in CATEGORIES]
        details.append({"id":case["id"],"mode":report.get("mode"),"status":report["status"],
                        "single_trials":report["single_trials"],"pair_trials":report["pair_trials"],
                        "admitted_candidates":len(candidates),
                        "unsampled_guard_edges":sum(count == 0 for guard in report.get("branch", {}).get("guards", [])
                                                    for count in guard["supplied_coverage"].values())})
        for candidate in candidates:
            generated += 1
            assert candidate.compiler_valid
            examined_sizes[str(len(candidate.proposal.edits))] += 1
            shape_counts[candidate.proposal.category] += 1
            verified = oracle.verify(candidate.proposed_code, "f", vectors(case), ExecutionLimits())
            discovery_passes += verified.status == Status.MATCHES_SUPPLIED_TESTS
            assert verified.status == Status.MATCHES_SUPPLIED_TESTS, (case["id"], candidate.proposed_code, verified.status)
    return {"results":details,"compiler_valid":fraction(generated,generated),
            "discovery_passes":fraction(discovery_passes,generated),
            "edit_counts":dict(examined_sizes),"categories":dict(shape_counts),"guided_latency":latency(times)}


def measured_case(client, case, version):
    request = dict(source=case["source"], entry_point="f", engine_version=version, vectors=case["vectors"], compare_candidates=True)
    data = worker_call(client, request)
    assert data["program"] == program_identity(case["source"])
    outcome = observation(case, data)
    exact = {repair_key(code) for code in case["references"]}
    holdout, original_holdout = [], None
    recommendation = data["guided_evidence"]["recommended_candidate"]
    if case["holdout_vectors"]:
        for choice in data["candidates"]:
            if choice["behavior"]["status"] != Status.MATCHES_SUPPLIED_TESTS:
                continue
            details = data.get("candidate_details", {}).get(choice["id"], {})
            metadata = {"category":data["candidate_categories"][choice["id"]], "edits":details.get("edits", [])}
            holdout.append(heldout_candidate(client, request, case, choice, metadata, exact, recommendation))
        if case["disposition"] == "fault" and data["original"]["status"] == Status.MATCHES_SUPPLIED_TESTS:
            fresh = worker_call(client, request | {"compare_candidates":False,"vectors":case["holdout_vectors"]})
            assert fresh["program"] == data["program"] and not fresh["candidates"]
            original_holdout = fresh["original"]["status"]
    usage = [sample for run in [data["original"], *(choice["behavior"] for choice in data["candidates"])]
             for sample in (run["execution"] or {}).get("samples", [])]
    return outcome | {
        "id":case["id"], "holdout":holdout, "original_holdout":original_holdout,
        "visible_suggestions":0 if data.get("review_presentation")=="OPTIONAL_COLLAPSED" else len(data["candidates"]),
        "max_peak_cells": max((sample["peak_cells"] for sample in usage), default=0),
        "max_call_depth": max((sample["call_depth"] for sample in usage), default=0),
        "compiled": len(data["candidates"]),
    }


def summarize(cases, runs):
    faults = [run for case,run in zip(cases,runs,strict=True) if case["disposition"]=="fault"]
    tested = [candidate for run in runs for candidate in run["holdout"]]
    results = [status for run in runs for status in run["candidate_results"]]
    return live_metrics(cases,runs) | {
        "candidate_discovery_passes":fraction(sum(status == Status.MATCHES_SUPPLIED_TESTS for status in results),len(results)),
        "candidate_holdout_passes":fraction(sum(choice["status"] == Status.MATCHES_SUPPLIED_TESTS for choice in tested),len(tested)),
        "exact_on_both_top1":fraction(sum(run["behavioral_rank"] == 1 and any(
            test["exact"] and test["status"] == Status.MATCHES_SUPPLIED_TESTS for test in run["holdout"]) for run in faults),len(faults)),
        "max_peak_cells":max(run["max_peak_cells"] for run in runs),
        "max_call_depth":max(run["max_call_depth"] for run in runs),
        "review_burden":review_burden(cases,runs),
    }


def policy_comparison(cases, profiles, archived_controls):
    phase8_pool = review_burden(cases, profiles["8"])
    retained = sum(row["retained"] for row in archived_controls)
    precision_only = {
        "base_engine": 8,
        "same_pool": phase8_pool,
        "archive": {"controls": len(archived_controls), "review_all": retained, "initially_visible": 0},
    }
    grid = next(run for run in profiles["85"] if run["id"] == "finite-relay-grid-fault")
    finite_domain = {
        "size": 9, "discovery": 4, "holdout": 5,
        "passing_candidates": [candidate["id"] for candidate in grid["holdout"]
                               if candidate["status"] == Status.MATCHES_SUPPLIED_TESTS],
    }
    return {"precision_policy_only": precision_only, "exhaustive_finite_domain": finite_domain}


def live(cases):
    from fastapi.testclient import TestClient
    from backend.app.main import app

    profiles = {"75":[],"8":[],"85":[]}
    durations = {profile:[] for profile in profiles}
    ambiguous = []
    with TestClient(app,base_url="http://127.0.0.1:8000",client=("127.0.0.1",41885)) as client:
        for _ in range(5):
            capability = client.get(URL+"/capability").json()
            if capability["status"] != "capacity_reached":
                break
            sleep(.25)
        assert capability["status"] == "available", capability
        for case in cases:
            for profile in profiles:
                start = perf_counter()
                profiles[profile].append(measured_case(client,case,int(profile)))
                durations[profile].append(1000*(perf_counter()-start))
            if case["disposition"] == "ambiguous":
                data = worker_call(client, {"source":case["source"],"entry_point":"f","engine_version":85,
                                           "vectors":[],"compare_candidates":True})
                assert data["guided_evidence"]["original"] == "INSUFFICIENT_SPECIFICATION"
                assert all("expected" not in probe for probe in data["probes"])
                ambiguous.append({"id":case["id"],"observational_probes":len(data["probes"]),
                                  "candidates":len(data["candidates"])})
        prior, _ = audit75()
        archived_controls = []
        for case in prior:
            if not (case["partition"] == "final" and case["disposition"] == "control"):
                continue
            settings = dict(source=case["source"],entry_point="f",vectors=case["vectors"],compare_candidates=True)
            old, new = [worker_call(client, settings | {"engine_version":version}) for version in (8,85)]
            if not old["candidates"]:
                continue
            assert [row["id"] for row in old["candidates"]] == [row["id"] for row in new["candidates"]]
            assert old["review_presentation"] == new["review_presentation"] == "OPTIONAL_COLLAPSED"
            archived_controls.append({"id":case["id"],"retained":len(new["candidates"]),"visible":0})
    return {"profiles":profiles,"statistics":{profile:summarize(cases,runs) for profile,runs in profiles.items()},
            **policy_comparison(cases, profiles, archived_controls),
            "roundtrip_with_holdout_latency":{profile:latency(times) for profile,times in durations.items()},
            "insufficient_information":ambiguous, "archived_control_presentation":archived_controls}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check",action="store_true")
    parser.add_argument("--live",action="store_true")
    parser.add_argument("--write",action="store_true")
    args = parser.parse_args()
    cases, leakage = audit()
    final = [case for case in cases if case["partition"] == "final"]
    history = [case for root in (PHASE8_ROOT,PHASE75_ROOT)
               for case in json.loads((root/"cases-v1.json").read_text())]
    targets = {"triad-overlap-fault","two-independent-coefficients-fault","rare-upper-adjustment-fault",
               "boolean-active-window-fault","counted-even-threshold-fault","coprime-count-fault"}
    oracle = MiniCOracle()
    static_results = {
        "audit":leakage,
        "original_faults_unseen_in_discovery":reference_suites(oracle,cases),
        "calibration":{name:static([case for case in cases if case["partition"]==name], CONFIGURATIONS)
                       for name in ("development","selection","calibration")},
        "final":static(final,CONFIGURATIONS),
        "mechanisms":mechanisms(oracle,final),
        "robustness":robustness(oracle,final),
        "archived_diagnostics":[diagnostic(case) for case in history if case["id"] in targets],
    }
    if args.check:
        assert any(case["disposition"] == "fault" for case in final)
        assert {item["id"] for item in static_results["archived_diagnostics"]} == targets
        assert static_results["mechanisms"]["edit_counts"].get("2", 0) > 0
        assert {"BRANCH_BOUNDARY_MISMATCH","LOOP_COUNT_CONSTRAINT"} <= static_results["mechanisms"]["categories"].keys()
    # Run the static synthesis twice on independent calls, without timing fields.
    for case in final:
        result = run_projection(case,phase85=True)
        assert stable(result.to_dict()) == stable(run_projection(case,phase85=True).to_dict()), case["id"]
    outputs = {"phase85-audit-v1":leakage, "phase85-static-v1":static_results}
    if args.live:
        results = live(final)
        if args.check:
            assert results["exhaustive_finite_domain"]["passing_candidates"]
            assert results["statistics"]["85"]["false_alerts"]["hits"] == 0
            assert results["statistics"]["85"]["exact_accepted_both"]["hits"] >= results["statistics"]["8"]["exact_accepted_both"]["hits"]
        outputs["phase85-live-v1"] = results
    for name,result in outputs.items():
        if args.write:
            (REPORTS/f"{name}.json").write_text(json.dumps(result,indent=2,ensure_ascii=False)+"\n")
    print(json.dumps({"audit":leakage,
                      "static":{name:run["guided_metrics"] for name,run in static_results["final"].items()
                                if "guided_metrics" in run},
                      **({"isolated":outputs["phase85-live-v1"]["statistics"]} if args.live else {})},indent=2))


if __name__ == "__main__":
    main()
