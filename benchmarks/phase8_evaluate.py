"""Replay Phase 8 synthesis, precision presentation and isolated holdouts."""
import argparse
from collections import Counter
import json
from time import perf_counter, sleep

from ai.behavior_oracle import ExecutionLimits, Status, program_identity
from ai.correction_safety import repair_key
from ai.intention_context import Example
from ai.intention_engine import analyze_intention
from ai.intention_phase8 import CATEGORIES, edit_cost
from vm.behavioral_executor import MiniCOracle

from .phase5_evaluate import fraction, latency
from .phase55_evaluate import stable
from .phase6_evaluate import REPORTS, URL, independent_references, metrics, row, vectors
from .phase65_evaluate import transform_paths
from .phase7_audit import audit as phase7_audit
from .phase7_evaluate import observation, static
from .phase75_audit import audit as phase75_audit
from .phase75_evaluate import check_reference_holdout, live_metrics
from .phase8_audit import audit

CONFIGURATIONS = {
    "phase65": {"phase65": True},
    "phase7": {"phase7": True},
    "phase75": {"phase75": True},
    "phase8_specification_only": {"phase8": True, "phase8_components": frozenset()},
    "phase8_arithmetic": {"phase8": True, "phase8_components": frozenset({"arithmetic"})},
    "phase8_interprocedural": {"phase8": True, "phase8_components": frozenset({"interprocedural"})},
    "phase8_full": {"phase8": True},
}


def discovery(case):
    return tuple(Example(v.arguments, v.expected) for v in vectors(case))


def historical_misses():
    lookup = {}
    for load in (phase7_audit, phase75_audit):
        cases, _ = load()
        lookup.update((c["id"],c) for c in cases)
    reasons = {
        "polygonal-layer-fault": "Adjacent coefficient in a checked closed form",
        "arithmetic-list-fault": "Missing predecessor under a multiplicative factor",
        "hexagonal-layer-fault": "Wrong signed offset in a local scale",
        "coprime-count-fault": "Loop and conditional dependency beyond the arithmetic projection",
    }
    results = []
    oracle = MiniCOracle()
    for id_, reason in reasons.items():
        case = lookup[id_]
        source, settings = case["source"], dict(phase6_entry="f",phase6_examples=discovery(case))
        previous = analyze_intention(source,phase75=True,**settings)
        current = analyze_intention(source,phase8=True,**settings)
        results.append({"id":id_,"previous":row(case,previous,previous.candidates),"current":row(case,current,current.candidates),
                        "fault_mechanism":reason,"constraints":current.program_analysis["phase8"]["constraints"],
                        "sample_agreement":sum(oracle.verify(c.proposed_code,"f",vectors(case),ExecutionLimits()).status
                                               == Status.MATCHES_SUPPLIED_TESTS for c in current.candidates)})
    return results


def robustness(cases):
    oracle = MiniCOracle()
    checks, changes = Counter(), []
    for case in cases:
        if case["disposition"] == "ambiguous":
            continue
        source, examples, suite = case["source"], discovery(case), vectors(case)
        before = oracle.verify(source,"f",suite,ExecutionLimits())
        settings = dict(phase8=True,phase6_examples=examples)
        first = analyze_intention(source,phase6_entry="f",**settings)
        categories = sorted(c.proposal.category for c in first.candidates)
        for method, altered, entry in transform_paths(source):
            after = oracle.verify(altered,entry,suite,ExecutionLimits())
            assert (before.status,[v.actual for v in before.observations]) == (after.status,[v.actual for v in after.observations]),(case["id"],method)
            result = analyze_intention(altered,phase6_entry=entry,**settings)
            assert result.context.compiler_valid and all(c.compiler_valid for c in result.candidates)
            checks[method] += 1
            if result.finding != first.finding or sorted(c.proposal.category for c in result.candidates)!=categories:
                changes.append({"id":case["id"],"transform":method})
            for candidate in result.to_dict()["candidates"]:
                assert candidate["source_snapshot"]==program_identity(altered)
                for edit in candidate["edits"]:
                    low, high = (edit["span"][key]["offset"] for key in ("start","end"))
                    assert 0<=low<high<=len(altered) and altered[low:high]==edit["original"]
    return {"checked":dict(checks),"total":sum(checks.values()),"changes":changes}


def candidate_evidence(cases):
    oracle = MiniCOracle()
    rows, costs = [], []
    for case in cases:
        result = analyze_intention(case["source"],phase8=True,phase6_entry="f",phase6_examples=discovery(case))
        generated = [c for c in result.candidates if c.proposal.category in CATEGORIES]
        for candidate in generated:
            edits = candidate.proposal.edits
            assert candidate.compiler_valid
            costs.extend(edit_cost(result.context, edit) for edit in edits)
            behavior = oracle.verify(candidate.proposed_code,"f",vectors(case),ExecutionLimits())
            # This trusted-fixture check catches divergence between arithmetic
            # source projection and the Mini-C compiler/VM.
            assert behavior.status == Status.MATCHES_SUPPLIED_TESTS, (case["id"],candidate.proposed_code,behavior.status)
        rows.append({"id":case["id"],"model":result.program_analysis["phase8"]["constraints"],
                     "generated_arithmetic":len(generated)})
    return {"rows":rows,"arithmetic_edit_costs":{str(cost): count for cost, count in sorted(Counter(costs).items())}}


def worker_call(client, payload):
    reply = client.post(URL,json=payload)
    assert reply.status_code==200,reply.text
    data=reply.json()
    assert data["availability"]["status"]=="available", data
    return data


def heldout_candidate(client, request, case, candidate, metadata, exact, recommended):
    assert not {tuple(v["arguments"]) for v in request["vectors"]} & {
        tuple(v["arguments"]) for v in case["holdout_vectors"]}
    # Held-out values never enter the request that generated candidates.
    data=worker_call(client,dict(source=candidate["source"],entry_point="f",engine_version=request["engine_version"],
                                 vectors=case["holdout_vectors"],compare_candidates=False))
    assert data["program"]==program_identity(candidate["source"]) and not data["candidates"]
    original=data["original"]
    examples=[]
    for observed in original["observations"]:
        vector=observed["vector"]
        if type(vector["expected"]) is not type(observed["actual"]) or vector["expected"]!=observed["actual"]:
            examples.append({"input":vector["arguments"],"expected":vector["expected"],"actual":observed["actual"]})
    issue=original["execution"]["issue"]
    if issue and issue["vector"] is not None:
        vector=case["holdout_vectors"][issue["vector"]]
        examples.append({"input":vector["arguments"],"expected":vector["expected"],"actual":None,"issue":issue["code"]})
    return {
        "id":candidate["id"],"category":metadata["category"],"edits":metadata["edits"],
        "exact":repair_key(candidate["source"]) in exact,"status":original["status"],
        "recommended":candidate["id"]==recommended,"counterexamples":examples,
        "steps":sum(sample["steps"] for sample in original["execution"]["samples"]),
    }


def run_case(client, case, version):
    request=dict(source=case["source"],entry_point="f",engine_version=version,vectors=case["vectors"],compare_candidates=True)
    data=worker_call(client,request)
    measured=observation(case,data)
    matching=[candidate for candidate in data["candidates"] if candidate["behavior"]["status"]==Status.MATCHES_SUPPLIED_TESTS]
    details=data.get("candidate_details",{})
    if matching and version==75:
        static_result=analyze_intention(case["source"],phase75=True,phase6_entry="f",phase6_examples=discovery(case)).to_dict()
        details={candidate["id"]:candidate for candidate in static_result["candidates"]}
    exact={repair_key(code) for code in case["references"]}
    holdout=[]
    if case["holdout_vectors"]:
        for candidate in matching:
            metadata={
                "category":data["candidate_categories"][candidate["id"]],
                "edits":details[candidate["id"]]["edits"],
            }
            holdout.append(heldout_candidate(client,request,case,candidate,metadata,exact,data["guided_evidence"]["recommended_candidate"]))
    visible=0 if data.get("review_presentation")=="OPTIONAL_COLLAPSED" else len(data["candidates"])
    return measured | {"id":case["id"],"holdout":holdout,"visible_suggestions":visible,
                       "domain":case["domain"],"review_presentation":data.get("review_presentation")}


def review_burden(cases, runs):
    controls=[row for case,row in zip(cases,runs,strict=True) if case["disposition"]=="control"]
    faults=[row for case,row in zip(cases,runs,strict=True) if case["disposition"]=="fault"]
    original_agreement=[row for row in controls if row["original"]==Status.MATCHES_SUPPLIED_TESTS]
    return {
        "review_all_same_pool": sum(len(row["candidate_ids"]) for row in controls),
        "initially_visible":sum(row["visible_suggestions"] for row in controls),
        "controls":len(controls),"original_control_agreement":len(original_agreement),
        "with_visible_suggestions":fraction(sum(row["visible_suggestions"]>0 for row in controls),len(controls)),
        "fault_candidate_recall_same_pool":fraction(sum(row["behavioral_match"] for row in faults),len(faults)),
        "compiled_candidates":sum(len(row["candidate_ids"]) for row in runs),
        "holdout_checks":sum(len(row["holdout"]) for row in runs),
        "holdout_passes":sum(test["status"]==Status.MATCHES_SUPPLIED_TESTS for row in runs for test in row["holdout"]),
        "recommended_holdout_failures":sum(test["recommended"] and test["status"]!=Status.MATCHES_SUPPLIED_TESTS
                                           for row in runs for test in row["holdout"]),
    }


def archived_review(client):
    archive=json.loads((REPORTS/"phase75-live-v1.json").read_text())
    prior={row["id"]:row for row in archive["profiles"]["75"] if row["candidate_ids"]}
    cases,_=phase75_audit()
    controls=[case for case in cases if case["partition"]=="final" and case["disposition"]=="control"
              and case["id"] in prior]
    measurements=[]
    for case in controls:
        base=dict(source=case["source"],entry_point="f",vectors=case["vectors"],compare_candidates=True)
        legacy, current=[worker_call(client,base | {"engine_version":version}) for version in (75,8)]
        old_ids=[row["id"] for row in legacy["candidates"]]
        new_ids=[row["id"] for row in current["candidates"]]
        assert old_ids==new_ids==prior[case["id"]]["candidate_ids"]
        assert current["guided_evidence"]["original"]=="ORIGINAL_MATCHES_SUPPLIED_TESTS"
        assert not current["guided_evidence"]["confirmed_fault"] and current["review_presentation"]=="OPTIONAL_COLLAPSED"
        measurements.append({"id":case["id"],"candidate_ids":new_ids,"previous_visible":len(old_ids),"initially_visible":0})
    assert len(measurements)==7
    return {"cases":measurements,"previous_visible":sum(row["previous_visible"] for row in measurements),
            "initially_visible":0,"pool_preserved":True}


def live(cases):
    from backend.app.main import app
    from fastapi.testclient import TestClient

    runs, durations, observation_only = {"75":[],"8":[]}, [], []
    with TestClient(app,base_url="http://127.0.0.1:8000",client=("127.0.0.1",41808)) as client:
        for _ in range(5):
            capability=client.get(URL+"/capability").json()
            if capability["status"]!="capacity_reached":
                break
            sleep(.25)
        assert capability["status"]=="available",capability
        for case in cases:
            for mode in (75,8):
                start=perf_counter()
                runs[str(mode)].append(run_case(client,case,mode))
                if mode==8:
                    durations.append(1000*(perf_counter()-start))
            if case["disposition"]=="ambiguous":
                data=worker_call(client,dict(source=case["source"],engine_version=8,entry_point="f",vectors=[],
                                             compare_candidates=True))
                assert data["guided_evidence"]["original"]=="INSUFFICIENT_SPECIFICATION"
                assert all("expected" not in probe for probe in data["probes"])
                observation_only.append(observation(case,data)|{"id":case["id"]})
        historical_presentation=archived_review(client)
    external=[(c,o) for c,o in zip(cases,runs["8"],strict=True) if c["provenance"]["group"]=="external_adaptation"]
    return {
        "profiles":runs,"metrics":{key:live_metrics(cases,rows) for key,rows in runs.items()},
        "external_phase8":live_metrics([c for c,_ in external],[o for _,o in external]),
        "presentation":{key:review_burden(cases,rows) for key,rows in runs.items()},
        "observation_only":observation_only,"latency":latency(durations),
        "archived_presentation_same_pool":historical_presentation,
    }


def evaluate(with_worker):
    cases, audit_report=audit()
    independent_references(cases)
    check_reference_holdout(cases)
    partitions={key:[case for case in cases if case["partition"]==key] for key in ("development","selection","calibration","final")}
    data={key:static(partition,CONFIGURATIONS) for key,partition in partitions.items()}
    final=partitions["final"]
    data.update(audit=audit_report,historical_misses=historical_misses(),robustness=robustness(final),
                arithmetic_witness=candidate_evidence(final))
    data["provenance"]={}
    for origin in ("external_adaptation","authored"):
        subset=[(case,result) for case,result in zip(final,data["final"]["phase8_full"]["guided_rows"],strict=True)
                if case["provenance"]["group"]==origin]
        data["provenance"][origin]=metrics([c for c,_ in subset],[r for _,r in subset])
    return data,live(final) if with_worker else None


if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--live",action="store_true")
    action=parser.add_mutually_exclusive_group()
    action.add_argument("--check",action="store_true")
    action.add_argument("--write",action="store_true")
    args=parser.parse_args()
    static_data,observed=evaluate(args.live)
    parts={"static":static_data,"audit":static_data["audit"],**({"live":observed} if args.live else {})}
    for name,report in parts.items():
        path=REPORTS/f"phase8-{name}-v1.json"
        if args.write:
            path.write_text(json.dumps(report,indent=2)+"\n")
        if args.check:
            assert stable(report)==stable(json.loads(path.read_text())),f"Phase 8 {name} replay changed"
    if args.check or args.write:
        print(f"Phase 8: {len(static_data['final']['phase8_full']['rows'])} admitted final cases")
    else:
        print(json.dumps(parts,indent=2))
