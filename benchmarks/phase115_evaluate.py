"""Evaluate Phase 11.5 without sharing independent holdout with synthesis."""
import argparse
from collections import Counter
import json
from time import perf_counter

from ai.behavior_oracle import ExecutionLimits, Status, Vector
from ai.intention_phase115 import CATEGORIES, COMPONENTS
from vm.behavioral_executor import MiniCOracle

from .phase5_evaluate import latency
from .phase6_evaluate import REPORTS, URL, rank, vectors
from .phase7_evaluate import static
from .phase85_evaluate import measured_case, observed, run_projection, summarize
from .phase9_evaluate import candidate_signature, provenance_metrics, reference_checks, rewrites
from .phase9_fixtures import ROOT as PHASE9
from .phase95_evaluate import provenance_static
from .phase10_fixtures import ROOT as PHASE10
from .phase105_fixtures import ROOT as PHASE105
from .phase11_fixtures import ROOT as PHASE11
from .phase115_audit import audit
from itertools import combinations_with_replacement
from ai.intention_context import build_context
from analysis_evidence.function_summary import analyze_program
from compiler import ast_nodes as ast
from .phase9_evaluate import graph_evidence

CONFIGURATIONS = {
    **{phase:{phase:True} for phase in ("phase65","phase10","phase105","phase11")},
    **{key:{"phase115":True,"phase115_components":frozenset({key})} for key in sorted(COMPONENTS)},
    **{f"without_{key}":{"phase115":True,"phase115_components":COMPONENTS-{key}} for key in sorted(COMPONENTS)},
    "phase115":{"phase115":True},
}
HISTORICAL = {
    "exponential-negative-endpoint-fault":(PHASE11,"A concrete negative recursive bound triggers an obsolete default reset."),
    "constant-interpolation-domain-fault":(PHASE105,"Guard-only and reordered probes can both match discovery."),
    "short-rotation-pivot-fault":(PHASE10,"Three unsafe neighbor branches need more than a tie refinement."),
    "shifted-missing-member-fault":(PHASE9,"The missing scan and dependent start, seed and index changes exceed two sites."),
}
SHADOW_CASES = ("iterative-leftmost-match-fault","duplicate-upper-endpoint-fault")


def archived_cases():
    return [(next(row for row in json.loads((root/"cases-v1.json").read_text()) if row["id"]==identifier),reason)
             for identifier,(root,reason) in HISTORICAL.items()]


def archive_projection():
    rows = []
    for case,reason in archived_cases():
        result = {"id":case["id"],"diagnosis":reason}
        for profile in ("phase11","phase115"):
            analysis = run_projection(case,**CONFIGURATIONS[profile])
            result[profile] = {"exact_rank":rank(case,[c.proposed_code for c in analysis.candidates]),
                               "categories":[c.proposal.category for c in analysis.candidates],
                               "projection":analysis.program_analysis[profile]}
        rows.append(result)
    return rows


def nested_variations(source):
    yield from rewrites(source)
    context=build_context(source)
    result=next((record.node for record in context.nodes if isinstance(record.node,ast.ReturnStatement)),None)
    if result is None:
        return
    start,end=result.span.start.offset,result.span.end.offset
    body=source[start:end]
    yield "nested_return",source[:start]+"{"+body+"}"+source[end:],"f"
    yield "independent_temporary",source[:start]+"{int unused_probe_value=7;}"+source[start:],"f"


def shadow_diagnostics(oracle):
    archived=json.loads((PHASE105/"cases-v1.json").read_text())
    rows=[]
    for identifier in SHADOW_CASES:
        case=next(row for row in archived if row["id"]==identifier)
        transformed=next(source for kind,source,_ in rewrites(case["source"]) if kind=="unused_shadow_scope")
        category="ENDPOINT_SEARCH_CONSTRAINT"
        suite=vectors(case)
        assert observed(oracle.verify(case["source"],"f",suite,ExecutionLimits()))==observed(
            oracle.verify(transformed,"f",suite,ExecutionLimits()))
        profiles={}
        states={}
        for variant,code in (("original",case["source"]),("shadow",transformed)):
            context=build_context(code)
            program=analyze_program(context,perf_counter()+2)
            states[variant]={
                "source":code,"cfg":graph_evidence(code,"f"),
                "returns":[{"span":record.node.span.to_dict(),"scope":record.function.name}
                           for record in context.nodes if isinstance(record.node,ast.ReturnStatement)],
                "lexical_bindings":[{"id":binding.id,"name":binding.name,
                                     "declaration":binding.declaration_span.to_dict()}
                                    for binding in program.bindings.symbols.values()],
                "definitions":[{"function":fn.function.name,"states":sum(len(v) for v in fn.flow.incoming)}
                               for fn in program.functions],
            }
            for name in ("phase11","phase115"):
                result=run_projection(case,source=code,**CONFIGURATIONS[name])
                profiles[name+"_"+variant]=[c.proposal.category for c in result.candidates]
        rows.append({"id":identifier,"first_divergence":"Phase 10.5 rejected the inert nested scope. Phase 11 and 11.5 retain the endpoint candidate.",
                     "states":states,"profiles":profiles,
                     "resolved":category in profiles["phase11_shadow"] and category in profiles["phase115_shadow"]})
    return rows


def mechanisms(oracle,cases):
    rows,categories,metamorphics,changes,timings = [],Counter(),Counter(),[],[]
    for case in cases:
        suite,source = vectors(case),case["source"]
        start = perf_counter()
        result = run_projection(case,phase115=True)
        timings.append(1000*(perf_counter()-start))
        report = result.program_analysis["phase115"]
        inline = [candidate for candidate in result.candidates if candidate.proposal.category in CATEGORIES]
        for candidate in inline:
            assert candidate.compiler_valid
            assert oracle.verify(candidate.proposed_code,"f",suite,ExecutionLimits()).status==Status.MATCHES_SUPPLIED_TESTS
            categories[candidate.proposal.category]+=1
        rows.append({"id":case["id"],"status":report["status"],"trials":report["trials"],
                     "categories":[c.proposal.category for c in inline],"details":report})
        original = observed(oracle.verify(source,"f",suite,ExecutionLimits()))
        signature = candidate_signature(oracle,result.candidates,"f",suite)
        for name,changed,entry in nested_variations(source):
            assert observed(oracle.verify(changed,entry,suite,ExecutionLimits()))==original,(case["id"],name)
            transformed = run_projection(case,source=changed,entry=entry,phase115=True)
            metamorphics[name]+=1
            if candidate_signature(oracle,transformed.candidates,entry,suite)!=signature:
                changes.append({"case":case["id"],"transformation":name,
                                "before":[c.proposal.category for c in result.candidates],
                                "after":[c.proposal.category for c in transformed.candidates]})
            for candidate in transformed.to_dict()["candidates"]:
                assert candidate["compiler_valid"] and candidate["requires_approval"]
                for edit in candidate["edits"]:
                    src,dst = (edit["span"][bound]["offset"] for bound in ("start","end"))
                    assert changed[src:dst]==edit["original"]
    return {"cases":rows,"categories":dict(categories),"latency":latency(timings),
            "metamorphic":{"tested":sum(metamorphics.values()),"transformations":dict(metamorphics),"changes":changes}}


def interpolation_domain(oracle):
    """Complete finite cross-product against an independent membership contract."""
    case=next(row for row,_ in archived_cases() if row["id"]=="constant-interpolation-domain-fault")
    candidates=[choice for choice in run_projection(case,phase115=True).candidates
                if choice.proposal.category=="INTERPOLATION_RELATIONAL_CONSTRAINT"]
    domain=(-1,0,2)
    keys=range(-2,4)
    runs=[{"id":choice.id,"edit_count":len(choice.proposal.edits),"matches":0,"failures":[]} for choice in candidates]
    differences=[]
    for cells in combinations_with_replacement(domain,4):
        for key in keys:
            expected=[i for i,value in enumerate(cells) if value==key] or [-1]
            observed_values=[]
            for choice,row in zip(candidates,runs,strict=True):
                vector=Vector(arguments=(key,*cells),expected=expected[0])
                result=oracle.verify(choice.proposed_code,"f",(vector,),ExecutionLimits())
                issue=result.execution.issue
                actual=issue.code if issue else result.observations[0].actual
                observed_values.append(actual)
                if actual in expected:
                    row["matches"]+=1
                else:
                    row["failures"].append({"arguments":list(vector.arguments),"allowed":expected,"observed":actual})
            if len(set(observed_values))>1:
                differences.append({"arguments":[key,*cells],"observed":observed_values,"allowed":expected})
    return {"scope":"ARCHIVED_DIAGNOSTIC_ONLY","cells":list(domain),"length":4,"keys":list(keys),
            "checked_inputs":len(tuple(combinations_with_replacement(domain,4)))*len(keys),
            "contract":"Return a matching index or -1 for absence.","alternatives":runs,"differences":differences}


def isolated(cases):
    from fastapi.testclient import TestClient
    from backend.app.main import app

    profiles = {str(version):[] for version in (10,105,11,115)}
    timings = {key:[] for key in profiles}
    with TestClient(app,base_url="http://127.0.0.1:8000",client=("127.0.0.1",41105)) as client:
        assert client.get(URL+"/capability").json()["status"]=="available"
        for case in cases:
            for version in profiles:
                start=perf_counter()
                profiles[version].append(measured_case(client,case,int(version)))
                timings[version].append(1000*(perf_counter()-start))
        archive = [measured_case(client,case,115) for case,_ in archived_cases()]
        interpolation=next(case for case,_ in archived_cases() if case["id"]=="constant-interpolation-domain-fault")
        discovery=dict(source=interpolation["source"],entry_point="f",vectors=interpolation["vectors"],compare_candidates=True)
        pair_review={}
        for version in (11,115):
            reply=client.post(URL,json=discovery|{"engine_version":version})
            assert reply.status_code==200,reply.text
            data=reply.json()
            pair_review[str(version)]={key:data[key] for key in ("candidate_pairs","probes","guided_evidence")}
        assert {tuple(row["candidates"]) for row in pair_review["11"]["candidate_pairs"]}=={
               tuple(row["candidates"]) for row in pair_review["115"]["candidate_pairs"]}
        assert pair_review["115"]["guided_evidence"]["recommended_candidate"] is None
    return {"profiles":profiles,"metrics":{key:summarize(cases,rows) for key,rows in profiles.items()},
            "by_provenance":{key:provenance_metrics(cases,rows) for key,rows in profiles.items()},
            "roundtrip_with_holdout_latency":{key:latency(values) for key,values in timings.items()},
            "historical_diagnostics_only":archive,"interpolation_pair_review":pair_review}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for option in ("check","live","write"):
        parser.add_argument(f"--{option}",action="store_true")
    args=parser.parse_args()
    cohort,leakage = audit()
    final = [case for case in cohort if case["partition"]=="final"]
    oracle = MiniCOracle()
    references = reference_checks(oracle,cohort)
    comparisons = static(final,CONFIGURATIONS)
    diagnostics = archive_projection()
    shadow = shadow_diagnostics(oracle)
    mechanism = mechanisms(oracle,final)
    interpolation = interpolation_domain(oracle)
    report = {"ablations":comparisons,"by_provenance":provenance_static(final,comparisons),
              "mechanisms":mechanism,"interpolation_finite_domain":interpolation,"historical_diagnostics_only":diagnostics,"shadow_diagnostics":shadow,"original_reference_checks":references,
              "separate_partitions":{split:static([c for c in cohort if c["partition"]==split],CONFIGURATIONS)
                                     for split in ("development","selection")}}
    if args.check:
        assert len(leakage["admitted_external_families"])==3
        assert interpolation["checked_inputs"]==90 and len(interpolation["alternatives"])==2
        assert all(not row["categories"] for row in mechanism["cases"] if row["id"].endswith("-control"))
        assert all(row["resolved"] for row in shadow)
    reports = {"phase115-audit-v1":leakage,"phase115-static-v1":report}
    if args.live:
        observed_results = isolated(final)
        if args.check:
            assert observed_results["metrics"]["115"]["false_alerts"]["hits"]==0
            for row in observed_results["profiles"]["115"]:
                if row["policy"]["original"] in {"RUNTIME_FAILURE","EXECUTION_LIMITED"}:
                    assert not row["policy"]["confirmed_fault"] and row["policy"]["recommended_candidate"] is None
        reports["phase115-live-v1"] = observed_results
    if args.write:
        for name,body in reports.items():
            (REPORTS/f"{name}.json").write_text(json.dumps(body,indent=2,ensure_ascii=False)+"\n")
    print(json.dumps({"cases":len(final),"categories":mechanism["categories"],
                      "static":report["by_provenance"]["phase115"],
                      **({"live":observed_results["by_provenance"]["115"]} if args.live else {})},indent=2))


if __name__=="__main__":
    main()
