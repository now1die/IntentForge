"""Evaluate bounded synthesis and a separate, isolated behavioral holdout."""
import argparse
from collections import Counter
import json
from time import perf_counter, sleep

from ai.behavior_oracle import ExecutionLimits, Status, Vector, program_identity
from ai.correction_safety import repair_key
from ai.intention_context import Example
from ai.intention_engine import analyze_intention
from vm.behavioral_executor import MiniCOracle

from .phase5_evaluate import fraction, latency
from .phase55_evaluate import stable
from .phase6_evaluate import REPORTS, URL, independent_references, metrics, row, vectors
from .phase65_evaluate import transform_paths
from .phase7_audit import audit as phase7_audit
from .phase7_evaluate import observation, static
from .phase75_audit import audit

CONFIGURATIONS = {
    "phase6": {"phase6": True},
    "phase65": {"phase65": True},
    "phase7": {"phase7": True},
    "phase75_robustness": {"phase75": True, "phase75_components": frozenset({"helper_layout"})},
    "phase75_nonunit": {"phase75": True, "phase75_components": frozenset({"nonunit"})},
    "phase75_dependencies": {"phase75": True, "phase75_components": frozenset({"dependencies"})},
    "phase75_full": {"phase75": True},
}
EXTERNAL_MISSES = {
    "josephus-ring-fault": ("recursive progress", "The recognized return excluded the remainder operation around the self-call.", "f(people,stride)"),
    "digital-root-fault": ("radix disagreement", "The loop lacked a quotient-to-remainder relation for the same binding.", "v=v/9"),
    "automorphic-tail-fault": ("radix disagreement", "The scale, threshold and quotient updates had no cross-statement invariant.", "temp/=100"),
    "polygonal-layer-fault": ("coefficient constant", "No rule inferred the intended closed-form coefficient from supplied examples.", "sides-3"),
    "manhattan-grid-fault": ("missing helper argument", "No helper argument dependency rule generated an alternative; the archived cases also lack a pair varying only the omitted input.", "gap(a,d)"),
    "arithmetic-list-fault": ("missing predecessor expression", "No synthesis rule generated a predecessor factor inside this nonrecursive scalar formula.", "count*difference"),
}


def archived_cases():
    cases, _ = phase7_audit()
    return {case["id"]: case for case in cases if case["partition"] == "final"}


def historical_external(cases):
    prior = json.loads((REPORTS/"phase7-static-v1.json").read_text())
    archived = {item["id"]:item for item in prior["final"]["phase7_full"]["guided_rows"]}
    live = json.loads((REPORTS/"phase7-live-v1.json").read_text())
    observations = dict(zip(live["ids"],live["phase7_full"],strict=True))
    results = []
    oracle = MiniCOracle()
    for name,(category, detail, snippet) in EXTERNAL_MISSES.items():
        case = cases[name]
        source = case["source"]
        index = source.index(snippet)
        examples = tuple(Example(v.arguments,v.expected) for v in vectors(case))
        old_analysis = analyze_intention(source,phase7=True,phase6_entry="f",phase6_examples=examples)
        analysis = analyze_intention(source,phase75=True,phase6_entry="f",phase6_examples=examples)
        assert archived[name]["rank"] is None and not old_analysis.candidates
        fn = next((item for item in old_analysis.program_analysis["functions"] if item["name"]=="f"), {})
        results.append({
            "id":name, "intended_behavior":case["specification"],"fault":category,"root_cause":detail,
            "offset":index,"fault_source":snippet,"reference":case["references"][0],
            "phase7_attempts":archived[name]["attempts"],"phase7_candidates":archived[name]["candidates"],
            "phase7_exact_rank":archived[name]["rank"],"original":observations[name]["original"],
            "issue":observations[name]["issue"],"phase7_conditions":len(fn.get("conditions",[])),
            "phase7_recursion":fn.get("recursion"),"phase7_finding":old_analysis.finding,
            "phase75":row(case,analysis,analysis.candidates),
            "phase75_archived_vector_matches": [
                {"exact": repair_key(item.proposed_code) == repair_key(case["references"][0]),
                 "observed": oracle.verify(item.proposed_code,"f",vectors(case),ExecutionLimits()).status}
                for item in analysis.candidates
            ],
        })
    return results


def robustness(cases, *, archived=False):
    engine = MiniCOracle()
    recorded = json.loads((REPORTS/"phase7-static-v1.json").read_text()) if archived else None
    selected = {(item["id"],item["transform"]) for item in recorded["metamorphic"]["changed"]} if archived else None
    counts, changes, details = Counter(), [], []
    for case in cases:
        if case["disposition"] == "ambiguous":
            continue
        if selected is not None and all(case["id"] != key for key,_ in selected):
            continue
        source, suite = case["source"], vectors(case)
        original = engine.verify(source,"f",suite,ExecutionLimits())
        settings = dict(phase75=True)
        base = analyze_intention(source,phase6_entry="f",**settings)
        categories = sorted(item.proposal.category for item in base.candidates)
        for mode, changed, entry in transform_paths(source):
            if selected is not None and (case["id"],mode) not in selected:
                continue
            result = engine.verify(changed,entry,suite,ExecutionLimits())
            assert (result.status,[v.actual for v in result.observations]) == (original.status,[v.actual for v in original.observations])
            current = analyze_intention(changed,phase6_entry=entry,**settings)
            assert current.context.compiler_valid and all(c.compiler_valid for c in current.candidates)
            observed = sorted(c.proposal.category for c in current.candidates)
            counts[mode] += 1
            row_id = {"id":case["id"],"transform":mode}
            if observed != categories or current.finding != base.finding:
                changes.append(row_id)
            for candidate in current.to_dict()["candidates"]:
                assert candidate["source_snapshot"] == program_identity(changed)
                for edit in candidate["edits"]:
                    start, end = (edit["span"][key]["offset"] for key in ("start","end"))
                    assert 0 <= start < end <= len(changed) and changed[start:end] == edit["original"]
            if selected is not None:
                old = analyze_intention(changed,phase7=True,phase6_entry=entry)
                assert not old.candidates and base.candidates
                details.append(row_id | {"phase7_categories":[],"phase75_categories":observed,"source":changed,
                                         "same_categories_as_original":observed==categories})
    if selected is not None:
        assert len(details)==len(selected)==2
    return {"total":sum(counts.values()),"checked":dict(counts),"changes":changes,"archived_details":details}


def helper_metamorphs():
    baseline = "int shift(int x){return x+2;}"
    caller = "int f(int n,int total){if(n<=0){return total;}return shift(f(n,total+1));}"
    variants = {
        "helper_local_temporary":"int shift(int x){int prior=x+2;return prior;}",
        "nested_unused_shadow":"int shift(int x){{int x=5;{int x=7;}}return x+2;}",
        "independent_declarations":"int shift(int x){int unused=5;int prior=x+2;return prior;}",
        "reordered_declarations":"int shift(int x){int prior=x+2;int unused=5;return prior;}",
    }
    suite = tuple(Vector(arguments=(n,a),expected=a+3*n) for n,a in [(0,1),(2,-1),(5,4)])
    oracle = MiniCOracle()
    original = oracle.verify(baseline+caller,"f",suite,ExecutionLimits())
    settings = dict(phase75=True,phase6_entry="f")
    prior = analyze_intention(baseline+caller,**settings).candidates
    previous, = prior
    rows = []
    for mode, helper in variants.items():
        source = helper+caller
        before = oracle.verify(source,"f",suite,ExecutionLimits())
        assert before.status==original.status and [r.actual for r in before.observations]==[r.actual for r in original.observations]
        analysis = analyze_intention(source,**settings)
        repair, = analysis.candidates
        artifact, = analysis.to_dict()["candidates"]
        assert repair.proposal.category==previous.proposal.category and repair.compiler_valid
        assert artifact["source_snapshot"]==program_identity(source) and repair.id!=previous.id
        result = oracle.verify(repair.proposed_code,"f",suite,ExecutionLimits())
        assert result.status==Status.MATCHES_SUPPLIED_TESTS
        rows.append(dict(transform=mode,id=repair.id,source_snapshot=artifact["source_snapshot"],status=result.status))
    return rows


def check_reference_holdout(cases):
    oracle = MiniCOracle()
    for case in cases:
        suites = case["vectors"] + case["holdout_vectors"]
        for source in case["references"] or [case["source"]]:
            checked = oracle.verify(source,"f",vectors({"vectors":suites}),ExecutionLimits())
            assert checked.status==Status.MATCHES_SUPPLIED_TESTS,(case["id"],checked.status)


def live_result(client, case, version):
    request = dict(source=case["source"],entry_point="f",engine_version=version, vectors=case["vectors"],compare_candidates=True)
    reply = client.post(URL,json=request)
    assert reply.status_code==200,reply.text
    data=reply.json()
    assert data["availability"]["status"]=="available",data
    outcome=observation(case,data)
    held=[]
    exact={repair_key(code) for code in case["references"]}
    if case["holdout_vectors"]:
        for candidate in data["candidates"]:
            if candidate["behavior"]["status"]!=Status.MATCHES_SUPPLIED_TESTS:
                continue
            packet = request | {"source":candidate["source"],"vectors":case["holdout_vectors"],"compare_candidates":False}
            check = client.post(URL,json=packet).json()
            assert check["availability"]["status"]=="available"
            assert check["program"]==program_identity(candidate["source"])
            appeared=check["original"]
            held.append({"id":candidate["id"],"exact":repair_key(candidate["source"]) in exact,
                         "status":appeared["status"],"steps":sum(v["steps"] for v in appeared["execution"]["samples"])})
    return outcome | {"id":case["id"],"holdout":held}


def live_metrics(cases, runs):
    faults=[run for case,run in zip(cases,runs,strict=True) if case["disposition"]=="fault"]
    controls=[run for case,run in zip(cases,runs,strict=True) if case["disposition"]=="control"]
    alerts=sum(run["policy"]["confirmed_fault"] for run in faults)
    false=sum(run["policy"]["confirmed_fault"] for run in controls)
    ranks={name:{f"top{n}":fraction(sum(run[name] is not None and run[name]<=n for run in faults),len(faults))
                  for n in (1,3)} for name in ("exact_rank","behavioral_rank")}
    return dict(
        fault_alerts=fraction(alerts,len(faults)), false_alerts=fraction(false,len(controls)),
        precision=fraction(alerts,alerts+false),
        correct_control_hypotheses=fraction(sum(bool(run["candidate_ids"]) for run in controls),len(controls)),
        exact_recall=fraction(sum(run["exact_rank"] is not None for run in faults),len(faults)),
        matching_discovery=fraction(sum(run["behavioral_match"] for run in faults),len(faults)),
        accepted_both=fraction(sum(any(test["status"]==Status.MATCHES_SUPPLIED_TESTS for test in run["holdout"]) for run in faults),len(faults)),
        exact_accepted_both=fraction(sum(any(test["exact"] and test["status"]==Status.MATCHES_SUPPLIED_TESTS for test in run["holdout"]) for run in faults),len(faults)),
        non_exact_accepted_both=sum(not t["exact"] and t["status"]==Status.MATCHES_SUPPLIED_TESTS for run in faults for t in run["holdout"]),
        contradicted_after_discovery=sum(t["status"]==Status.MISMATCHES_SUPPLIED_TESTS for run in faults for t in run["holdout"]),
        recommendations=fraction(sum(run["policy"]["recommended_candidate"] is not None for run in runs),len(runs)),
        abstentions=sum(run["policy"]["recommended_candidate"] is None for run in runs),
        ambiguity=sum(run["tests_matching_candidates"]>1 for run in runs),
        original_statuses=dict(Counter(run["original"] for run in runs)),
        holdout_steps=sum(test["steps"] for run in runs for test in run["holdout"]),
        **{key:sum(run[key] for run in runs) for key in ("probe_steps","observed_steps","new_pairs","probes","runtime_fault_observations")},
        **ranks,
    )


def live(cases):
    from backend.app.main import app
    from fastapi.testclient import TestClient

    runs, times, probes = {"7":[],"75":[]}, [], []
    with TestClient(app,base_url="http://127.0.0.1:8000",client=("127.0.0.1",41928)) as client:
        for _ in range(5):
            capability=client.get(URL+"/capability").json()
            if capability["status"]!="capacity_reached":
                break
            sleep(.25)
        assert capability["status"]=="available",capability
        for case in cases:
            for version in (7,75):
                start=perf_counter()
                result=live_result(client,case,version)
                runs[str(version)].append(result)
                if version==75:
                    times.append(1000*(perf_counter()-start))
            if case["disposition"]=="ambiguous":
                data=client.post(URL,json=dict(source=case["source"],entry_point="f",engine_version=75,
                                               vectors=[],compare_candidates=True)).json()
                assert data["availability"]["status"]=="available"
                assert data["guided_evidence"]["original"]=="INSUFFICIENT_SPECIFICATION"
                assert all("expected" not in p for p in data["probes"])
                probes.append(observation(case,data)|{"id":case["id"]})
    report={"profiles":runs,"metrics":{key:live_metrics(cases,values) for key,values in runs.items()}}
    external=[(case, run) for case,run in zip(cases,runs["75"],strict=True) if case["provenance"]["group"]=="external_adaptation"]
    return report | {"latency":latency(times),"observation_only":probes,
                     "external_phase75":live_metrics([c for c,_ in external],[r for _,r in external])}


def evaluate(with_worker):
    cases, audit_report = audit()
    independent_references(cases)
    check_reference_holdout(cases)
    partitions={key:[case for case in cases if case["partition"]==key] for key in ("development","selection","calibration","final")}
    results={key:static(partition,CONFIGURATIONS) for key,partition in partitions.items()}
    old=archived_cases()
    results["external_history"]=historical_external(old)
    results["archived_robustness"]=robustness(old.values(),archived=True)
    results["helper_metamorphs"]=helper_metamorphs()
    final=partitions["final"]
    results["metamorphic"]=robustness(final)
    results["audit"]=audit_report
    results["static_provenance"]={}
    for category in ("authored","external_adaptation"):
        subset=[(case,value) for case,value in zip(final,results["final"]["phase75_full"]["guided_rows"],strict=True)
                if case["provenance"]["group"]==category]
        results["static_provenance"][category]=metrics([case for case,_ in subset],[row for _,row in subset])
    return results, live(final) if with_worker else None


if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--live",action="store_true")
    method=parser.add_mutually_exclusive_group()
    method.add_argument("--check",action="store_true")
    method.add_argument("--write",action="store_true")
    args=parser.parse_args()
    result, observed=evaluate(args.live)
    parts={"static":result,"audit":result["audit"], **({"live":observed} if args.live else {})}
    for label, report in parts.items():
        path=REPORTS/f"phase75-{label}-v1.json"
        if args.check:
            assert stable(report)==stable(json.loads(path.read_text())),f"Phase 7.5 {label} replay changed"
        if args.write:
            path.write_text(json.dumps(report,indent=2)+"\n")
    if args.check or args.write:
        print(f"Phase 7.5: {len(result['final']['phase75_full']['rows'])} admitted final cases")
    else:
        print(json.dumps(parts,indent=2))
