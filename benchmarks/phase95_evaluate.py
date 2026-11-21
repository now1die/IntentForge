"""Compare Phase 9.5 ablations, archived misses and isolated independent holdout."""
import argparse
from collections import Counter
import json
from time import perf_counter, sleep

from ai.behavior_oracle import ExecutionLimits, Status
from ai.intention_phase95 import CATEGORIES
from vm.behavioral_executor import MiniCOracle

from .phase5_evaluate import fraction, latency
from .phase6_evaluate import REPORTS, URL, rank, vectors
from .phase7_evaluate import static
from .phase85_evaluate import measured_case, observed, run_projection, summarize
from .phase9_evaluate import candidate_signature, graph_evidence, provenance_metrics, reference_checks, rewrites
from .phase9_fixtures import ROOT as PHASE9
from .phase75_fixtures import ROOT as PHASE75
from .phase95_audit import audit

CONFIGURATIONS = {
    "phase65":{"phase65":True},
    "phase85":{"phase85":True},
    "phase9":{"phase9":True},
    "domain":{"phase95":True,"phase95_components":frozenset({"domain"})},
    "windows":{"phase95":True,"phase95_components":frozenset({"windows"})},
    "range":{"phase95":True,"phase95_components":frozenset({"range"})},
    "without_helpers":{"phase95":True,"phase95_components":frozenset({"domain","windows","range"})},
    "phase95":{"phase95":True},
}


def archived_cases():
    return [case for case in json.loads((PHASE9/"cases-v1.json").read_text())
            if case["fault_origin"]=="adapted-real-defect"]


def historical(oracle):
    diagnoses = {
        "lower-end-prime-classification-fault": "Missing pure entry guard before the even shortcut and trial loop.",
        "last-product-window-fault": "The exclusive origin bound omits the final width-adjusted start. A zero-window input exposes the sentinel.",
        "shifted-missing-member-fault": "No reaching minimum in the defective lexical scope. The reference derives both endpoints and uses a data-dependent XOR helper.",
    }
    result = []
    for case in archived_cases():
        before,after = (run_projection(case,**{phase:True}) for phase in ("phase9","phase95"))
        baseline = oracle.verify(case["source"],"f",vectors(case),ExecutionLimits())
        result.append({
            "id":case["id"],"diagnosis":diagnoses[case["id"]],
            "source":case["source"],"reference":case["references"][0],
            "sample_vectors":case["vectors"],"original_status":baseline.status,
            "evidence":graph_evidence(case["source"],"f"),
            "phase9_candidates":len(before.candidates),"phase95_projection":after.program_analysis["phase95"],
            "phase95_exact_rank":rank(case,[candidate.proposed_code for candidate in after.candidates]),
            "candidate_categories":[candidate.proposal.category for candidate in after.candidates],
        })
    coprime = next(case for case in json.loads((PHASE75/"cases-v1.json").read_text()) if case["id"]=="coprime-count-fault")
    return {"archived":result,"coprime":run_projection(coprime,phase95=True).program_analysis["phase95"]}


def mechanisms(oracle,cases):
    trials, categories, transformations, differences, elapsed = [], Counter(), Counter(), [], []
    for case in cases:
        suite, source = vectors(case), case["source"]
        start = perf_counter()
        result = run_projection(case,phase95=True)
        elapsed.append(1000*(perf_counter()-start))
        report = result.program_analysis["phase95"]
        tested = [candidate for candidate in result.candidates if candidate.proposal.category in CATEGORIES]
        for candidate in tested:
            behavior = oracle.verify(candidate.proposed_code,"f",suite,ExecutionLimits())
            assert candidate.compiler_valid and behavior.status==Status.MATCHES_SUPPLIED_TESTS, (case["id"],candidate.proposed_code)
            categories[candidate.proposal.category] += 1
        trials.append({"id":case["id"],"status":report["status"],"trial_count":report["trials"],"emitted":len(tested)})
        original = observed(oracle.verify(source,"f",suite,ExecutionLimits()))
        signature = candidate_signature(oracle,result.candidates,"f",suite)
        for kind,changed,entry in rewrites(source):
            assert observed(oracle.verify(changed,entry,suite,ExecutionLimits()))==original, (case["id"],kind)
            altered = run_projection(case,source=changed,entry=entry,phase95=True)
            transformations[kind] += 1
            if candidate_signature(oracle,altered.candidates,entry,suite)!=signature:
                differences.append({"case":case["id"],"transform":kind,
                                    "original":[c.proposal.category for c in result.candidates],
                                    "transformed":[c.proposal.category for c in altered.candidates]})
            for candidate in altered.to_dict()["candidates"]:
                assert candidate["compiler_valid"] and candidate["requires_approval"]
                for edit in candidate["edits"]:
                    lo,hi=(edit["span"][pos]["offset"] for pos in ("start","end"))
                    assert edit["original"]==changed[lo:hi]
    return {"cases":trials,"categories":dict(categories),"latency":latency(elapsed),
            "metamorphic":{"tested":sum(transformations.values()),"types":dict(transformations),"differences":differences}}


def provenance_static(cases,reports):
    out={}
    for profile,result in reports.items():
        if "guided_rows" not in result:
            continue
        out[profile]={}
        for origin in ("adapted-real-defect","project-injected"):
            targets=[index for index,case in enumerate(cases) if case["fault_origin"]==origin]
            out[profile][origin]={mode:fraction(sum(result[key][i]["rank"] is not None for i in targets),len(targets))
                                  for mode,key in (("code_only","rows"),("guided","guided_rows"))}
    return out


def live(cases, static_report):
    from fastapi.testclient import TestClient
    from backend.app.main import app

    profiles={str(version):[] for version in (85,9,95)}
    times={key:[] for key in profiles}
    with TestClient(app,base_url="http://127.0.0.1:8000",client=("127.0.0.1",41995)) as client:
        for _ in range(5):
            capability=client.get(URL+"/capability").json()
            if capability["status"]!="capacity_reached":
                break
            sleep(.25)
        assert capability["status"]=="available", capability
        for case in cases:
            for key in profiles:
                start=perf_counter()
                profiles[key].append(measured_case(client,case,int(key)))
                times[key].append(1000*(perf_counter()-start))
        archived=[measured_case(client,case,95) for case in archived_cases()]
    unsupported = {row["id"] for row in static_report["cases"] if row["status"] in {
                   "UNSUPPORTED_PROJECTION","ANALYSIS_LIMITED","INSUFFICIENT_SUCCESSFUL_SAMPLES"}}
    basis={version:provenance_metrics(cases,runs) for version,runs in profiles.items()}
    basis["95"]["unsupported_projection"]={
        "count":len(unsupported),
        "faults":sum(case["id"] in unsupported and case["disposition"]=="fault" for case in cases),
        "holdout_recovered_by_inherited_engines":sum(run["id"] in unsupported and any(
            hit["status"]==Status.MATCHES_SUPPLIED_TESTS for hit in run["holdout"]) for run in profiles["95"]),
    }
    return {"profiles":profiles,"metrics":{version:summarize(cases,runs) for version,runs in profiles.items()},
            "by_provenance":basis,"latency":{version:latency(values) for version,values in times.items()},
            "historical_diagnostics_only":archived}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check",action="store_true")
    parser.add_argument("--live",action="store_true")
    parser.add_argument("--write",action="store_true")
    options=parser.parse_args()
    cohort,leakage=audit()
    final=[row for row in cohort if row["partition"]=="final"]
    oracle=MiniCOracle()
    profiles=static(final,CONFIGURATIONS)
    detail=mechanisms(oracle,final)
    history=historical(oracle)
    report={"ablations":profiles,"by_provenance":provenance_static(final,profiles),
            "mechanisms":detail,"historical":history,"original_reference_checks":reference_checks(oracle,cohort),
            "selection":{split:static([case for case in cohort if case["partition"]==split],CONFIGURATIONS)
                         for split in ("development","selection","calibration")}}
    if options.check:
        assert history["coprime"]["status"]=="UNSUPPORTED_PROJECTION"
        assert set(detail["categories"])==CATEGORIES
        assert all(item["phase9_candidates"]==0 for item in history["archived"])
        assert len(leakage["admitted_external_families"])>=4
    outputs={"phase95-audit-v1":leakage,"phase95-static-v1":report}
    if options.live:
        isolated=live(final,detail)
        if options.check:
            assert isolated["metrics"]["95"]["false_alerts"]["hits"]==0
            assert isolated["by_provenance"]["95"]["adapted_real_defect"]["count"]==len(leakage["admitted_external_families"])
        outputs["phase95-live-v1"]=isolated
    if options.write:
        for name,body in outputs.items():
            (REPORTS/f"{name}.json").write_text(json.dumps(body,indent=2,ensure_ascii=False)+"\n")
    print(json.dumps({"audit":leakage,"static":report["by_provenance"],
                      **({"isolated":outputs["phase95-live-v1"]["metrics"]} if options.live else {})},indent=2))


if __name__=="__main__":
    main()
