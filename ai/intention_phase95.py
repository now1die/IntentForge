"""Finite evidence for entry guards, loop boundaries, and lexical range origins."""
from collections import Counter
from dataclasses import dataclass
from time import monotonic

from compiler.source_location import SourceSpan

from .intention_candidates import Edit, Evidence, Proposal, point
from .intention_phase8 import ProjectionLimit, UnsupportedProjection, edit_cost
from .intention_phase95_flow import FlowProjection, MAX_LOOP_POINTS, RANGE, WINDOW, project
from .specification import INT_MAX, INT_MIN

DOMAIN = "DOMAIN_BASE_CASE_CONSTRAINT"
CATEGORIES = frozenset({DOMAIN, WINDOW, RANGE})
COMPONENTS = frozenset({"domain","windows","range","helpers"})
MAX_TRIALS = 24
MAX_PROPOSALS = 4


@dataclass(frozen=True, slots=True)
class Guard:
    position: int
    lower: bool
    threshold: int
    value: int | bool
    affected: tuple
    edit: Edit


def guard_choices(model, item, spec, rows):
    examples = spec.examples
    wrong = [i for i,(sample,row) in enumerate(zip(rows,examples,strict=True))
             if sample.value is None or sample.value != row.expected_return]
    if len(wrong)<2:
        return []
    sentinel = examples[wrong[0]].expected_return
    if any(examples[i].expected_return!=sentinel for i in wrong):
        return []
    different = [i for i,row in enumerate(examples) if i not in wrong and row.expected_return!=sentinel]
    if not different:
        return []

    opening = next((token for token in model.context.parsed.tokens if token.lexeme=="{"
                    and token.span.start.offset==item.function.body.span.start.offset),None)
    if opening is None:
        return []
    literal = (str(sentinel).lower() if type(sentinel) is bool else str(sentinel))
    candidates = []
    for position,(name,kind) in enumerate(spec.parameters):
        if kind!="int":
            continue
        failing = {examples[i].args[position] for i in wrong}
        protected = [examples[i].args[position] for i in different]
        if len(failing)<2:
            continue
        for lower in (True,False):
            threshold = max(failing)+1 if lower else min(failing)-1
            if not INT_MIN<=threshold<=INT_MAX or threshold not in protected:
                continue
            if any(value<threshold if lower else value>threshold for value in protected):
                continue
            operator = "<" if lower else ">"
            affected = tuple(i+1 for i,row in enumerate(examples)
                             if (row.args[position]<threshold if lower else row.args[position]>threshold))
            if not set(i+1 for i in wrong)<=set(affected):
                continue
            edit = Edit(point(opening.span.end),f"\n    if ({name} {operator} {threshold}) {{ return {literal}; }}\n")
            candidates.append(Guard(position,lower,threshold,sentinel,affected,edit))
    return candidates


def sample_evidence(model, rows):
    loops, exits, helpers = [], Counter(), Counter()
    for label,function in model.models.items():
        for site,loop in function.loops.items():
            indices = [row.loops.get((label,site),()) for row in rows]
            loops.append({"function":label,"span":loop.span.to_dict(),"relation":loop.relation,
                          "bound":loop.bound,"origin":loop.init,"latch":loop.latch,
                          "indexed_bindings":list(loop.indexed_bindings),"point_limit":MAX_LOOP_POINTS,
                          "samples":[{"iterations":len(points),"first":points[0] if points else None,
                                      "last":points[-1] if points else None} for points in indices]})
    for row in rows:
        exits.update(row.exits)
        helpers.update(row.helpers)
    return {"loops":loops,"exits":dict(sorted(exits.items())),"helper_calls":dict(sorted(helpers.items())),
            "sample_issues":[row.issue for row in rows]}


def synthesize(context, program, spec, enabled):
    report = {"status":"INCOMPLETE_SPECIFICATION","scope":"SUPPLIED_EXAMPLES_ONLY","trials":0,
              "components":sorted(enabled),"compatible_candidates":0}
    if not enabled:
        return (), report | {"status":"COMPONENT_DISABLED"}
    if len({example.args for example in spec.examples})<2 or spec.return_type not in {"int","bool"}:
        return (), report
    if program.status!="AVAILABLE":
        return (),report | {"status":program.status}
    item = next(row for row in program.functions if row.function.name==spec.function)
    model = FlowProjection(context,program,enabled)
    expected = [row.expected_return for row in spec.examples]
    compatible = []
    try:
        model.compile(spec.function)
        rows = [project(model,spec.function,row.args,trace=True) for row in spec.examples]
        report |= sample_evidence(model,rows)
        if [row.value for row in rows]==expected:
            return (),report | {"status":"CONSTRAINTS_ALREADY_AGREE"}
        # A fault on every supplied row gives no successful behavior to preserve.
        if all(row.value is None for row in rows):
            return (),report | {"status":"INSUFFICIENT_SUCCESSFUL_SAMPLES"}
        if "domain" in enabled:
            for guard in guard_choices(model,item,spec,rows):
                report["trials"] += 1
                # The guard affects only examples with trusted sentinel outputs.
                if all(spec.examples[i-1].expected_return==guard.value for i in guard.affected):
                    name = spec.parameters[guard.position][0]
                    compatible.append((DOMAIN,guard.edit,
                        {"guard":{"parameter":name,"comparison":"<" if guard.lower else ">",
                                  "threshold":guard.threshold,"expected_return":guard.value,
                                  "covered_examples":list(guard.affected)}}))

        # Cheap trials first. Accept only if every supplied point is modeled and agrees.
        changes = sorted(model.changes.values(), key=lambda change:
                         (edit_cost(context,change.edit),change.edit.span.start.offset,change.edit.replacement))
        for change in changes:
            if report["trials"]>=MAX_TRIALS or monotonic()>=program.deadline:
                raise ProjectionLimit
            report["trials"] += 1
            results = []
            for row in spec.examples:
                sample = project(model,spec.function,row.args,(change,),trace=True)
                if sample.value!=row.expected_return:
                    break
                results.append(sample)
            if len(results)!=len(expected):
                continue
            if change.category==RANGE:
                affected = [i for i,before in enumerate(rows) if before.value!=expected[i]]
                origins = {points[0] for i in affected for site,points in results[i].loops.items()
                           if points and results[i].loops.get(site)!=rows[i].loops.get(site)}
                if len(affected)<2 or len(origins)<2:
                    continue
            compatible.append((change.category,change.edit,sample_evidence(model,results)))
    except UnsupportedProjection:
        return (),report | {"status":"UNSUPPORTED_PROJECTION"}
    except ProjectionLimit:
        return (),report | {"status":"ANALYSIS_LIMITED"}

    compatible.sort(key=lambda row:(edit_cost(context,row[1]),row[1].span.start.offset,row[1].replacement))
    report["compatible_candidates"] = len(compatible)
    report["status"] = ("MULTIPLE_COMPATIBLE_EDITS" if len(compatible)>1 else
                        "COMPATIBLE_EDIT" if compatible else "NO_COMPATIBLE_EDIT")
    report["witnesses"] = [{"category":category,"edit":{"span":edit.span.to_dict(),"replacement":edit.replacement},**witness}
                           for category,edit,witness in compatible[:MAX_PROPOSALS]]
    output = []
    for category,edit,witness in compatible[:MAX_PROPOSALS]:
        span = edit.span if category!=DOMAIN else SourceSpan(item.function.body.span.start,item.function.body.span.end)
        detail = ("A pure entry guard supplies the specified result on the sampled boundary inputs."
                  if category==DOMAIN else "The control edit fits every typed expectation in the bounded CFG projection.")
        output.append(Proposal((edit,),category,(Evidence("FINITE_CONSTRAINT_WITNESS",detail,span),),
                               "Review the finite evidence and verify the candidate before applying.",
                               "ControlFlow","guard" if category==DOMAIN else "loop",type_match=True,
                               counter_evidence=(Evidence("FINITE_DOMAIN","Inputs outside the supplied samples remain unverified.",span),)))
    return tuple(output),report
