"""Evidence-driven fixed-array, search, handoff and pure helper repairs."""
from collections import Counter
from itertools import combinations
from time import monotonic

from .intention_candidates import Evidence, Proposal
from .intention_phase8 import ProjectionLimit, UnsupportedProjection, edit_cost
from .intention_phase95 import sample_evidence
from .intention_phase95_flow import RANGE as PRESERVED_RANGE, project
from .intention_phase10_flow import ARRAY, EXPANSION, HELPER, RANGE, SEARCH, Progress, SearchProjection

COMPONENTS = frozenset({"array","search","expansion","range","helper"})
CATEGORIES = frozenset({ARRAY,EXPANSION,HELPER,RANGE,SEARCH})
MAX_TRIALS = 24
MAX_PROPOSALS = 4


def source_evidence(model,results,witnesses):
    report=sample_evidence(model,results)
    report["arrays"]=sorted(model.arrays.values(),key=lambda row:row["span"]["start"]["offset"])
    report["accesses"]=[
        {"sample":sample,"span":model.sites[site].to_dict(),**facts}
        for sample,witness in enumerate(witnesses,1) for site,facts in witness.accesses.items()
    ][:80]
    report["search_intervals"]=[
        {"function":name,"lower":model.bindings.symbols[interval.low].name,
         "upper":model.bindings.symbols[interval.high].name,"midpoint":model.bindings.symbols[interval.midpoint].name,
         "extent":interval.length,"inclusive":interval.inclusive,"span":interval.span.to_dict(),
         "recursive":bool(interval.positions),"sampled_frames":[witness.frames.get(name,[]) for witness in witnesses]
         if interval.positions else []}
        for name,intervals in model.intervals.items() for interval in intervals
    ]
    report["progress"]=[
        {"function":name,"kind":loop.mode,"span":loop.span.to_dict(),"guard":loop.bound,
         "samples":[{"count":len(points),"first":points[0] if points else None,"last":points[-1] if points else None}
                    for points in (row.loops.get((name,site),()) for row in results)]}
        for name,function in model.models.items() for site,loop in function.loops.items() if hasattr(loop,"mode")
    ]
    return report


def sample(model,spec,changes=()):
    results,witnesses=[],[]
    for example in spec.examples:
        witness=Progress(model,changes)
        value=project(model,spec.function,example.args,changes,trace=True,observer=witness)
        results.append(value)
        witnesses.append(witness)
        if changes and value.value!=example.expected_return:
            return None
    return results,witnesses


def synthesize(context,program,spec,enabled):
    report={"status":"INCOMPLETE_SPECIFICATION","scope":"SUPPLIED_EXAMPLES_ONLY","trials":0,
            "components":sorted(enabled),"compatible_candidates":0}
    if not enabled:
        return (),report | {"status":"COMPONENT_DISABLED"}
    if len({row.args for row in spec.examples})<2 or spec.return_type not in {"int","bool"}:
        return (),report
    if program.status!="AVAILABLE":
        return (),report | {"status":program.status}
    if context.parsed.ast.globals:
        return (),report | {"status":"UNSUPPORTED_PROJECTION"}
    model=SearchProjection(context,program,enabled)
    counts=Counter(row.expected_return for row in spec.examples if type(row.expected_return) is int and row.expected_return<0)
    hit_values={row.expected_return for row in spec.examples
                if type(row.expected_return) is int and row.expected_return>=0}
    model.sentinel=next(iter(counts)) if len(counts)==1 and len(hit_values)>=2 else None
    expected=[example.expected_return for example in spec.examples]
    compatible=[]
    try:
        model.compile(spec.function)
        results,witnesses=sample(model,spec)
        report |= source_evidence(model,results,witnesses)
        original=[row.value for row in results]
        if original==expected:
            return (),report | {"status":"CONSTRAINTS_ALREADY_AGREE"}
        if all(value is None for value in original):
            return (),report | {"status":"INSUFFICIENT_SUCCESSFUL_SAMPLES"}
        mutations=sorted(model.changes.values(),key=lambda change:
                         (edit_cost(context,change.edit),change.edit.span.start.offset,change.edit.replacement))

        def trial(edits):
            report["trials"]+=1
            if report["trials"]>MAX_TRIALS or monotonic()>=program.deadline:
                raise ProjectionLimit
            changed=sample(model,spec,edits)
            if changed is None:
                return
            sampled,_=changed
            category=edits[0].category
            if category==PRESERVED_RANGE:
                changed_origins={points[0] for i,row in enumerate(sampled)
                                 if original[i]!=expected[i]
                                 for site,points in row.loops.items() if points and points!=results[i].loops.get(site)}
                if len(changed_origins)<2:
                    return
                category=RANGE
            compatible.append((category,tuple(change.edit for change in edits)))

        for change in mutations:
            if change.action=="entry_guard" and sum(value is None for value in original)<2:
                continue
            trial((change,))
        if not compatible and "expansion" in enabled:
            for first,second in combinations((change for change in mutations if change.category==EXPANSION),2):
                if {first.action,second.action}!={"delta","reference"}:
                    continue
                edits=tuple(sorted((first,second),key=lambda change:change.edit.span.start.offset))
                if edits[0].edit.span.end.offset<=edits[1].edit.span.start.offset:
                    trial(edits)
    except UnsupportedProjection:
        return (),report | {"status":"UNSUPPORTED_PROJECTION"}
    except ProjectionLimit:
        return (),report | {"status":"ANALYSIS_LIMITED"}

    compatible.sort(key=lambda row:(len(row[1]),sum(edit_cost(context,edit) for edit in row[1]),
                                    tuple((edit.span.start.offset,edit.replacement) for edit in row[1])))
    report["compatible_candidates"]=len(compatible)
    report["status"]="MULTIPLE_COMPATIBLE_EDITS" if len(compatible)>1 else "COMPATIBLE_EDIT" if compatible else "NO_COMPATIBLE_EDIT"
    proposals=[]
    report["witnesses"]=[]
    for category,edits in compatible[:MAX_PROPOSALS]:
        report["witnesses"].append({"category":category,"edits":[{"span":edit.span.to_dict(),"replacement":edit.replacement}
                                                                for edit in edits]})
        facts=tuple(Evidence("FINITE_CONSTRAINT_WITNESS","This edit set agrees on the supplied typed examples under checked projection.",
                             edit.span) for edit in edits)
        proposals.append(Proposal(edits,category,facts,"Verify this proposal on the isolated worker before approving the source diff.",
                                  "ControlFlow","search",type_match=True,counter_evidence=(
                                      Evidence("FINITE_DOMAIN","Index and progress evidence cover the supplied samples.",edits[0].span),)))
    return tuple(proposals),report
