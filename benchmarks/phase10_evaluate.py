"""Measure bounded search repair against frozen discovery and held-out inputs."""
import argparse
from collections import Counter
import json
from time import perf_counter

from ai.behavior_oracle import ExecutionLimits, Status
from ai.intention_phase10 import CATEGORIES, COMPONENTS
from vm.behavioral_executor import MiniCOracle

from .phase5_evaluate import latency
from .phase6_evaluate import REPORTS, rank, vectors
from .phase7_evaluate import static
from .phase85_evaluate import measured_case, observed, run_projection, summarize
from .phase9_evaluate import candidate_signature, provenance_metrics, reference_checks, rewrites
from .phase95_evaluate import provenance_static
from .phase95_fixtures import ROOT as PHASE95
from .phase9_fixtures import ROOT as PHASE9
from .phase75_fixtures import ROOT as PHASE75
from .phase10_audit import audit

CONFIGURATIONS = {
    **{phase:{phase:True} for phase in ("phase65","phase85","phase9","phase95")},
    **{name:{"phase10":True,"phase10_components":frozenset({name})} for name in sorted(COMPONENTS)},
    **{f"without_{name}":{"phase10":True,"phase10_components":COMPONENTS-{name}} for name in sorted(COMPONENTS)},
    "phase10":{"phase10":True},
}
DIAGNOSTICS = {
    "recursive-search-upper-bound-fault": (PHASE95,"Unchecked inclusive caller endpoint."),
    "expanding-search-boundary-fault": (PHASE95,"Incorrect expansion handoff and nonconstant absence result."),
    "shifted-missing-member-fault": (PHASE9,"Both a missing range scan and an unsupported data-dependent XOR helper."),
    "coprime-count-fault": (PHASE75,"Divisor magnitude decreases through the Euclidean helper."),
}


def archived_cases():
    return [(next(case for case in json.loads((root/"cases-v1.json").read_text()) if case["id"]==identifier),
             diagnosis) for identifier,(root,diagnosis) in DIAGNOSTICS.items()]


def historical():
    results = []
    for case, diagnosis in archived_cases():
        item = {"id":case["id"],"diagnosis":diagnosis,"holdout_vectors":len(case["holdout_vectors"])}
        for version in ("phase95","phase10"):
            result = run_projection(case,**CONFIGURATIONS[version])
            item[version] = {
                "exact_rank":rank(case,[c.proposed_code for c in result.candidates]),
                "categories":[c.proposal.category for c in result.candidates],
                "projection":result.program_analysis[version],
            }
        results.append(item)
    return results


def mechanisms(oracle, cases):
    rows,categories,transforms,differences,elapsed = [],Counter(),Counter(),[],[]
    for case in cases:
        suite,source = vectors(case),case["source"]
        start = perf_counter()
        result = run_projection(case,phase10=True)
        elapsed.append(1000*(perf_counter()-start))
        projection = result.program_analysis["phase10"]
        choices = [c for c in result.candidates if c.proposal.category in CATEGORIES]
        for choice in choices:
            assert choice.compiler_valid
            assert oracle.verify(choice.proposed_code,"f",suite,ExecutionLimits()).status == Status.MATCHES_SUPPLIED_TESTS
            categories[choice.proposal.category] += 1
        rows.append({"id":case["id"],"status":projection["status"],"issues":projection.get("sample_issues", []),
                     "trial_count":projection.get("trials", 0),"emitted":len(choices),"evidence":projection})
        original = observed(oracle.verify(source,"f",suite,ExecutionLimits()))
        signature = candidate_signature(oracle,result.candidates,"f",suite)
        for name,changed,entry in rewrites(source):
            assert observed(oracle.verify(changed,entry,suite,ExecutionLimits()))==original,(case["id"],name)
            altered = run_projection(case,source=changed,entry=entry,phase10=True)
            transforms[name] += 1
            if candidate_signature(oracle,altered.candidates,entry,suite)!=signature:
                differences.append({"id":case["id"],"rewrite":name,"before":[c.proposal.category for c in result.candidates],
                                    "after":[c.proposal.category for c in altered.candidates]})
            for candidate in altered.to_dict()["candidates"]:
                assert candidate["compiler_valid"] and candidate["requires_approval"]
                for edit in candidate["edits"]:
                    lo,hi = (edit["span"][endpoint]["offset"] for endpoint in ("start","end"))
                    assert edit["original"]==changed[lo:hi]
    return {"cases":rows,"categories":dict(categories),"latency":latency(elapsed),
            "metamorphic":{"tested":sum(transforms.values()),"types":dict(transforms),"differences":differences}}


def live(cases, detail):
    from fastapi.testclient import TestClient
    from backend.app.main import app
    from .phase6_evaluate import URL

    versions = ("85","9","95","10")
    profiles,times = {key:[] for key in versions},{key:[] for key in versions}
    with TestClient(app,base_url="http://127.0.0.1:8000",client=("127.0.0.1",41010)) as client:
        capability = client.get(URL+"/capability").json()
        assert capability["status"]=="available",capability
        for case in cases:
            for key in versions:
                start = perf_counter()
                profiles[key].append(measured_case(client,case,int(key)))
                times[key].append(1000*(perf_counter()-start))
        diagnostics = [measured_case(client,case,10) for case,_ in archived_cases()]
    unsupported = {row["id"] for row in detail["cases"] if row["status"] in {
        "UNSUPPORTED_PROJECTION","ANALYSIS_LIMITED","INSUFFICIENT_SUCCESSFUL_SAMPLES"}}
    return {"profiles":profiles, "metrics":{ver:summarize(cases,results) for ver,results in profiles.items()},
            "by_provenance":{ver:provenance_metrics(cases,results) for ver,results in profiles.items()},
            "roundtrip_with_holdout_latency":{ver:latency(values) for ver,values in times.items()},
            "unsupported_projection":{"ids":sorted(unsupported),"heldout_repairs_from_inherited_profiles":[
                row["id"] for row in profiles["10"] if row["id"] in unsupported and
                any(hit["status"]==Status.MATCHES_SUPPLIED_TESTS for hit in row["holdout"])]},
            "historical_diagnostics_only":diagnostics}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for option in ("check","live","write"):
        parser.add_argument(f"--{option}",action="store_true")
    args = parser.parse_args()
    cohort,leakage = audit()
    final = [row for row in cohort if row["partition"]=="final"]
    oracle = MiniCOracle()
    references = reference_checks(oracle,cohort)
    comparisons = static(final,CONFIGURATIONS)
    found = mechanisms(oracle,final)
    diagnostics = historical()
    report = {"ablations":comparisons,"by_provenance":provenance_static(final,comparisons),"mechanisms":found,
              "historical_diagnostics_only":diagnostics,"original_reference_checks":references,
              "separate_partitions":{split:static([c for c in cohort if c["partition"]==split],CONFIGURATIONS)
                                    for split in ("development","selection","calibration")}}
    if args.check:
        assert len(leakage["admitted_external_families"])==4
        assert all(row["phase95"]["exact_rank"] is None for row in diagnostics)
        assert diagnostics[2]["phase10"]["exact_rank"] is None
        assert all(row["phase10"]["exact_rank"]==1 for i,row in enumerate(diagnostics) if i!=2)
        assert all(not row["emitted"] for row in found["cases"] if row["id"].endswith("-control"))
    reports = {"phase10-audit-v1":leakage,"phase10-static-v1":report}
    if args.live:
        isolated = live(final,found)
        if args.check:
            assert isolated["metrics"]["10"]["false_alerts"]["hits"]==0
            assert isolated["by_provenance"]["10"]["adapted_real_defect"]["count"]==4
            for row in isolated["profiles"]["10"]:
                if row["policy"]["original"]=="RUNTIME_FAILURE":
                    assert not row["policy"]["confirmed_fault"] and row["policy"]["recommended_candidate"] is None
        reports["phase10-live-v1"] = isolated
    if args.write:
        for name,body in reports.items():
            (REPORTS/f"{name}.json").write_text(json.dumps(body,indent=2,ensure_ascii=False)+"\n")
    brief = {"final_cases":len(final),"categories":found["categories"],"metamorphic":found["metamorphic"],
             "by_provenance":report["by_provenance"]["phase10"]}
    if args.live:
        brief["isolated"] = {key:isolated["by_provenance"][key] for key in ("95","10")}
    print(json.dumps(brief,indent=2))


if __name__=="__main__":
    main()
