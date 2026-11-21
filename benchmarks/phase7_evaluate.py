"""Replay Phase 7 static, precision, and isolated probe comparisons."""
import argparse
from collections import Counter
import json
import os
from pathlib import Path
from time import perf_counter, sleep

from ai.behavior_oracle import ExecutionLimits, Status, Vector
from ai.intention_context import Example, Requirement
from ai.intention_engine import analyze_intention
from vm.behavioral_executor import MiniCOracle

from .phase5_evaluate import fraction, latency
from .phase55_evaluate import stable
from .phase6_evaluate import REPORTS, URL, independent_references, metrics, rank, row, vectors
from .phase65_audit import audit as audit_phase65
from .phase65_evaluate import transform_paths
from .phase7_audit import audit

CONFIGURATIONS = {
    "phase6": {"phase6": True},
    "phase65": {"phase65": True},
    "phase7_layout_only": {"phase7": True, "phase7_components": frozenset({"layout"})},
    "phase7_helpers_only": {"phase7": True, "phase7_components": frozenset({"helpers"})},
    "phase7_full": {"phase7": True},
}


def run_static(case, options, examples=(), requirement=None):
    report = analyze_intention(case["source"], requirement, phase6_entry="f", phase6_examples=examples, **options)
    assert report.context.compiler_valid and all(c.compiler_valid for c in report.candidates)
    return report


def static(cases, configurations=CONFIGURATIONS):
    readings = {}
    for configuration, options in configurations.items():
        timings, static_rows, guided = [], [], []
        for case in cases:
            start = perf_counter()
            analysis = run_static(case, options)
            timings.append(1000*(perf_counter()-start))
            static_rows.append(row(case, analysis, analysis.candidates))
            examples = tuple(Example(tuple(vector.arguments), vector.expected) for vector in vectors(case))
            analysis = run_static(case, options, examples)
            guided.append(row(case, analysis, analysis.candidates))
        readings[configuration] = {"metrics": metrics(cases, static_rows), "guided_metrics": metrics(cases, guided),
                                   "rows": static_rows, "guided_rows": guided,
                                   **({"latency": latency(timings)} if timings else {})}
    for condition, key in (("natural_language", "description"), ("explicit", "expression")):
        selection = [case for case in cases if case["requirement"] and (("description" in case["requirement"]) == (key == "description"))]
        scores = {}
        for profile in ("phase65", tuple(configurations)[-1]):
            values = []
            for case in selection:
                result = run_static(case, configurations[profile], requirement=Requirement(function="f", **case["requirement"]))
                values.append(row(case, result, result.candidates) | {"requirement_status": result.requirement_status})
            scores[profile] = {"metrics": metrics(selection, values), "rows": values}
        readings[condition] = scores
    return readings


def reproduce_phase65():
    recorded = json.loads((REPORTS/"phase65-static-v1.json").read_text())["robustness"]
    failure_modes = {(report["id"],report["transform"]) for report in recorded if not report["categories_preserved"]}
    final, _ = audit_phase65()
    oracle = MiniCOracle()
    comparisons = []
    for case in final:
        if "fault" not in case["id"] or case["partition"] != "final":
            continue
        source, spec = case["source"], vectors(case)
        original = oracle.verify(source, "f", spec, ExecutionLimits())
        for mode, changed, entry in transform_paths(source):
            if (case["id"], mode) not in failure_modes:
                continue
            transformed = oracle.verify(changed, entry, spec, ExecutionLimits())
            assert transformed.status == original.status and [value.actual for value in transformed.observations] == [
                value.actual for value in original.observations]
            settings = dict(phase6_entry=entry)
            old = analyze_intention(changed, phase65=True, **settings)
            current = analyze_intention(changed, phase7=True, **settings)
            reference = analyze_intention(source, phase7=True, phase6_entry="f")
            categories = [item.proposal.category for item in current.candidates]
            assert not old.candidates and reference.candidates and current.context.compiler_valid
            for item in current.candidates:
                for edit in item.proposal.edits:
                    assert 0 <= edit.span.start.offset < edit.span.end.offset <= len(changed)
            comparisons.append(dict(id=case["id"], transform=mode, prior_categories=[],
                                    current_categories=categories, consistent=current.finding == reference.finding
                                    and categories == [item.proposal.category for item in reference.candidates]))
    assert len(comparisons) == len(failure_modes) == 6
    return comparisons


def metamorphic_final(cases):
    engine = MiniCOracle()
    counts = Counter()
    changes = []
    for case in cases:
        if case["disposition"] == "ambiguous":
            continue
        source, suite = case["source"], vectors(case)
        original = engine.verify(source,"f",suite,ExecutionLimits())
        base = analyze_intention(source, phase7=True, phase6_entry="f")
        categories = [item.proposal.category for item in base.candidates]
        for mode, changed, entry in transform_paths(source):
            after = engine.verify(changed,entry,suite,ExecutionLimits())
            assert after.status == original.status and [r.actual for r in after.observations] == [r.actual for r in original.observations], (case["id"],mode)
            report = analyze_intention(changed, phase7=True, phase6_entry=entry)
            assert report.context.compiler_valid and all(item.compiler_valid for item in report.candidates)
            counts[mode] += 1
            if report.finding != base.finding or [item.proposal.category for item in report.candidates] != categories:
                changes.append({"id":case["id"],"transform":mode})
    baseline = "int f(int n){int left=n+2;int right=n*3;if(n<0){return left;}return right;}"
    left, right = "int left=n+2;", "int right=n*3;"
    reordered = baseline.replace(left+right, right+left)
    suite = tuple(Vector(arguments=(n,), expected=n+2 if n<0 else n*3) for n in (-2,0,9))
    original, changed = [engine.verify(source,"f",suite,ExecutionLimits()) for source in (baseline,reordered)]
    assert original.status == changed.status == Status.MATCHES_SUPPLIED_TESTS
    old, new = [analyze_intention(source, phase7=True) for source in (baseline,reordered)]
    counts["independent_declaration_reorder"] += 1
    if old.finding != new.finding or [item.proposal.category for item in old.candidates] != [
            item.proposal.category for item in new.candidates]:
        changes.append({"id":"independent-declarations","transform":"independent_declaration_reorder"})
    return dict(checked=dict(counts), changed=changes, total=sum(counts.values()))


def probe_replay():
    from backend.app.routes.behavioral import validate_identity, wire
    from execution_service.contracts import Batch, BatchResult, LocalLimits, Program, TestVector

    source = "int f(int n){if(n<=1){return n;}return f(n-1)+f(n-2);}"
    variants = {
        "lagged_difference": (source, source.replace(")+f",")-f"), (2,),1),
        "joint_path_transition": ("int f(int x,int mode){if(mode<=2){return x+2;}return x*3;}",
                                  "int f(int x,int mode){if(mode<=2){return x+2;}return x*4;}",(3,2),5),
        "equivalent_under_probes": ("int f(int x){if(x<=2){return x;}return 2;}",
                                    "int f(int x){if(x<=2){return x+0;}return 2;}",(1,),1),
        "runtime_difference": ("int f(int x){if(x<3){return 1;}return 1;}",
                               "int f(int x){if(x<3){return 1;}return 8/(x-4);}",(2,),1),
    }
    result = {}
    for name, (a,b,args,expected) in variants.items():
        result[name] = {}
        programs = (Program(source=a),Program(source=a,candidate_id="IR-000000000001"),
                    Program(source=b,candidate_id="IR-000000000002"))
        for mode in (5,7):
            batch = Batch(entry_point="f", engine_version=mode, limits=LocalLimits(), trace=False, programs=programs,
                          vectors=(TestVector(arguments=args, expected=expected),))
            reply = wire(Path(os.environ["INTENTFORGE_VM_SOCKET"]),"/internal/verify",batch.model_dump_json().encode())
            assert reply["availability"]["status"] == "available"
            returned = BatchResult.model_validate(reply["result"])
            validate_identity(batch, returned)
            probes = returned.probes
            result[name][str(mode)] = dict(steps=sum(p.steps for p in probes), tested_inputs=len(probes),
                                           new_pairs=sum(p.new_pairs for p in probes),
                                           redundant_probes=sum(p.separated_pairs > 0 and p.new_pairs == 0 for p in probes),
                                           runtime_fault_observations=sum(v.status=="runtime_failure" for p in probes for v in p.candidates),
                                           distinguishing_inputs=[list(p.arguments) for p in probes if p.new_pairs])
    return result


def observation(case, response_data):
    choices = {item["id"]:item for item in response_data["candidates"]}
    review = response_data["review_order"]
    assert set(choices) == set(review) and response_data["requires_approval"]
    runs = [response_data["original"], *(item["behavior"] for item in choices.values())]
    probes = response_data["probes"]
    observed_steps = sum(sample["steps"] for run in runs if run["execution"] for sample in run["execution"]["samples"])
    probe_steps = sum(probe["steps"] for probe in probes)
    assert observed_steps + probe_steps <= 200000
    passing = [choices[key]["source"] for key in review
               if choices[key]["behavior"]["status"] == Status.MATCHES_SUPPLIED_TESTS]
    return {
        "original":runs[0]["status"], "issue":((runs[0]["execution"] or {}).get("issue") or {}).get("code"),
        "candidate_ids":list(choices), "tests_matching_candidates":len(passing),
        "candidate_results":[item["behavior"]["status"] for item in choices.values()],
        "exact_rank": rank(case,[item["source"] for item in choices.values()]),
        "behavioral_rank": rank(case,[choices[key]["source"] for key in review]),
        "exact_test_agreement": bool(rank(case,passing)),
        "first_matching_exact": bool(rank(case, passing[:1])),
        "behavioral_match": bool(passing), "observed_steps": observed_steps,"probe_steps":probe_steps,
        "new_pairs":sum(probe["new_pairs"] for probe in probes), "probes":len(probes),
        "redundant_probes":sum(probe["separated_pairs"]>0 and probe["new_pairs"]==0 for probe in probes),
        "runtime_fault_observations":sum(v["status"]=="runtime_failure" for probe in probes for v in probe["candidates"]),
        "pair_statuses": [item["status"] for item in response_data.get("candidate_pairs",[])],
        "policy":response_data.get("guided_evidence"),
    }


def policy_row(case, static_alert, legacy, guided):
    mismatch = legacy["original"] == Status.MISMATCHES_SUPPLIED_TESTS
    matches = legacy["original"] == Status.MATCHES_SUPPLIED_TESTS
    candidate = legacy["tests_matching_candidates"] > 0
    unique = mismatch and legacy["tests_matching_candidates"] == 1
    combined = guided if guided is not None else legacy
    recommendation = combined["policy"]["recommended_candidate"] is not None if combined["policy"] else unique
    return {
        "id":case["id"],
        "phase65": [static_alert, candidate],
        "original_mismatch_gate": [mismatch, mismatch and candidate],
        "original_match_suppression": [mismatch or static_alert and not matches, candidate],
        "evidence_tier_only": [static_alert, unique],
        "combined_same_pool": [mismatch, unique],
        "phase7_full": [combined["original"] == Status.MISMATCHES_SUPPLIED_TESTS, recommendation],
    }


def policy_metrics(cases, evidence, original, latest):
    faults = [i for i,c in enumerate(cases) if c["disposition"]=="fault"]
    controls = [i for i,c in enumerate(cases) if c["disposition"]=="control"]
    report = {}
    for policy in (key for key in evidence[0] if key != "id"):
        pool = latest if policy == "phase7_full" else original
        alerts = sum(evidence[i][policy][0] for i in faults)
        false = sum(evidence[i][policy][0] for i in controls)
        reviews = [i for i,result in enumerate(evidence) if result[policy][1]]
        report[policy] = {
            "fault_alerts":fraction(alerts,len(faults)), "false_alerts":fraction(false,len(controls)),
            "alert_precision":fraction(alerts,alerts+false),
            "candidate_recall":fraction(sum(pool[i]["behavioral_match"] for i in faults),len(faults)),
            "exact_recall":fraction(sum(pool[i]["exact_rank"] is not None for i in faults),len(faults)),
            "review_coverage":fraction(len(reviews),len(cases)),
            "incorrect_recommendations":fraction(sum(i in controls or i in faults and not pool[i]["first_matching_exact"] for i in reviews),len(reviews)),
            "abstentions":len(cases)-len(reviews),
            "passing_repairs_not_promoted":sum(pool[i]["behavioral_match"] and i not in reviews for i in faults),
        }
    return report


def historical_precision(client):
    archive = json.loads((REPORTS/"phase65-static-v1.json").read_text())
    alerts = {row["id"] for row in archive["final"]["rows"]["combined_guided"] if row["alert"]}
    admitted, _ = audit_phase65()
    results = []
    for case in admitted:
        if case["partition"] != "final" or case["disposition"] != "control" or case["id"] not in alerts:
            continue
        payload = dict(source=case["source"], entry_point="f", vectors=case["vectors"], compare_candidates=True)
        baseline, revised = [client.post(URL,json=payload | {"engine_version":profile}).json() for profile in (65,7)]
        assert baseline["availability"]["status"] == revised["availability"]["status"] == "available"
        assert baseline["original"]["status"] == Status.MATCHES_SUPPLIED_TESTS
        assert not revised["guided_evidence"]["confirmed_fault"]
        results.append({"id":case["id"],"prior_guided_alert":True,"confirmed_mismatch":revised["guided_evidence"]["confirmed_fault"],
                        "prior_candidates":len(baseline["candidates"]),"retained_hypotheses":len(revised["candidates"])})
    assert len(results) == 4
    return results


def live(cases, previous_guided):
    from fastapi.testclient import TestClient
    from backend.app.main import app

    answers, old, new, observed, durations = [], [], [], [], []
    with TestClient(app, base_url="http://127.0.0.1:8000", client=("127.0.0.1",41700)) as client:
        for _ in range(5):
            capability = client.get(URL+"/capability").json()
            if capability["status"] != "capacity_reached":
                break
            sleep(.25)
        assert capability["status"] == "available", capability
        for case, baseline in zip(cases,previous_guided,strict=True):
            payload = dict(source=case["source"],entry_point="f",compare_candidates=True,vectors=case["vectors"])
            result = {}
            for profile in (65,7):
                start = perf_counter()
                returned = client.post(URL,json=payload | {"engine_version":profile})
                assert returned.status_code == 200, returned.text
                data = returned.json()
                assert data["availability"]["status"]=="available", data
                result[profile] = observation(case,data)
                if profile==7:
                    durations.append(1000*(perf_counter()-start))
            old.append(result[65])
            new.append(result[7])
            answers.append(policy_row(case,baseline["alert"],old[-1],new[-1]))
            if case["disposition"] == "ambiguous":
                data = client.post(URL,json=payload | {"vectors":[],"engine_version":7}).json()
                assert data["availability"]["status"] == "available"
                assert data["guided_evidence"]["original"] == "INSUFFICIENT_SPECIFICATION"
                assert data["comparison_status"] is None and all("expected" not in p for p in data["probes"])
                observed.append({"id":case["id"],**observation(case,data)})
        historical = historical_precision(client)
    faults = [i for i,c in enumerate(cases) if c["disposition"]=="fault"]
    ranks = {}
    for name, pool in (("phase65",old),("phase7_full",new)):
        ranks[name] = {metric:{f"top{n}":fraction(sum(pool[i][metric] is not None and pool[i][metric] <= n for i in faults),len(faults))
                               for n in (1,3)} for metric in ("exact_rank","behavioral_rank")}
    return {"ids":[case["id"] for case in cases],"phase65":old,"phase7_full":new,"policy_rows":answers,
            "policy_metrics":policy_metrics(cases,answers,old,new),"same_pool_rank":ranks,"observation_only":observed,
            "probe_ablations":probe_replay(),"archived_false_alert_replay":historical,"latency":latency(durations)}


def evaluate(use_worker):
    cases, audit_report = audit()
    independent_references(cases)
    for case in cases:
        if case["disposition"] == "ambiguous":
            assert MiniCOracle().verify(case["source"],"f",vectors(case),ExecutionLimits()).status == Status.MATCHES_SUPPLIED_TESTS
    partitions = {key:[c for c in cases if c["partition"]==key] for key in ("development","selection","calibration","final")}
    reports = {key:static(rows) for key,rows in partitions.items()}
    final = partitions["final"]
    reports["audit"] = audit_report
    reports["reproduced_phase65"] = reproduce_phase65()
    reports["metamorphic"] = metamorphic_final(final)
    reports["provenance_metrics"] = {}
    for origin in ("external_adaptation","authored"):
        for profile in ("phase65","phase7_full"):
            for mode in ("rows","guided_rows"):
                selected = [(case,r) for case,r in zip(final,reports["final"][profile][mode],strict=True)
                            if case["provenance"]["group"] == origin]
                reports["provenance_metrics"][f"{origin}/{profile}/{mode}"] = metrics(
                    [case for case,_ in selected],[r for _,r in selected])
    return reports, live(final,reports["final"]["phase65"]["guided_rows"]) if use_worker else None


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--live",action="store_true")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--check",action="store_true")
    mode.add_argument("--write",action="store_true")
    args = parser.parse_args()
    summary, behavior = evaluate(args.live)
    output = {"static":summary,"audit":summary["audit"]}
    if args.live:
        output["live"] = behavior
    for name, report in output.items():
        path = REPORTS/f"phase7-{name}-v1.json"
        if args.check:
            assert stable(json.loads(path.read_text())) == stable(report), f"Phase 7 {name} replay changed"
        if args.write:
            path.write_text(json.dumps(report,indent=2)+"\n")
    if args.check or args.write:
        print(f"Phase 7: {len(summary['final']['phase7_full']['rows'])} admitted final cases")
    else:
        print(json.dumps(output,indent=2))
