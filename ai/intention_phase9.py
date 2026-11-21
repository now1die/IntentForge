"""Bounded normalization, scalar transfer and finite repair extensions for engine 9."""
from itertools import combinations, product
from time import monotonic

from .intention_candidates import Evidence, Proposal
from .intention_phase8 import Projector, ProjectionLimit, UnsupportedProjection, edit_cost, substitution
from .intention_phase85 import (
    MAX_PAIR_SITES, MAX_PAIR_TRIALS, MAX_PROPOSALS, MAX_SINGLE_TRIALS, ScalarProjection,
    branch_value, branch_witness, branches,
)
from .intention_phase9_loops import build_loop, loop_value

COMPONENTS = frozenset({"normalization", "variable_steps", "mixed_updates", "runtime", "cross_branch"})
CATEGORIES = frozenset({"GENERALIZED_LOOP_CONSTRAINT", "RUNTIME_CONSTRAINT", "CROSS_BRANCH_COEFFICIENTS"})


class LocalizedArithmetic(ArithmeticError):
    def __init__(self, origin, operator, left, right):
        self.origin = origin
        self.operator = operator
        self.operands = (left, right)
        self.code = "ZERO_DIVISOR" if operator in {"/", "%"} and right == 0 else "INT32_OVERFLOW"


def localize(origin, operator, left, right):
    raise LocalizedArithmetic(origin, operator, left, right)


def inside(outer, inner):
    return outer.start.offset <= inner.start.offset and inner.end.offset <= outer.end.offset


def cross_pairs(variants, observations, expected, collect, report, deadline):
    if len(observations) < 3:
        return []
    groups = {}
    for change, changed in variants:
        if change.action != "literal" or any(old[2] != new[2] for old, new in zip(observations, changed, strict=True)):
            continue
        repaired = {i for i, (old, new, wanted) in enumerate(zip(observations, changed, expected, strict=True))
                    if old[0] != wanted and new[0] == wanted}
        if repaired and (change.origin in groups or len(groups) < MAX_PAIR_SITES):
            groups.setdefault(change.origin, []).append((change, repaired))
    output = []
    for left, right in combinations(groups.values(), 2):
        for (a, fixed_a), (b, fixed_b) in product(left, right):
            if monotonic() >= deadline or report["pair_trials"] >= MAX_PAIR_TRIALS:
                raise ProjectionLimit
            if fixed_a & fixed_b or {observations[i][2] for i in fixed_a} & {observations[i][2] for i in fixed_b}:
                continue
            first, last = sorted((a, b), key=lambda change: change.edit.span.start.offset)
            if first.edit.span.end.offset > last.edit.span.start.offset:
                continue
            report["pair_trials"] += 1
            checked = collect((first, last))
            if checked is not None and tuple(row[0] for row in checked) == expected:
                output.append((first, last))
    return output


def synthesize(context, program, links, helpers, spec, enabled):
    report = {"status": "INCOMPLETE_SPECIFICATION", "components": sorted(enabled),
              "single_trials": 0, "pair_trials": 0, "compatible_candidates": 0, "scope": "SUPPLIED_EXAMPLES_ONLY"}
    if not enabled:
        return (), report | {"status": "COMPONENT_DISABLED"}
    examples = spec.examples
    if len({example.args for example in examples}) < 2:
        return (), report
    if program.status != "AVAILABLE":
        return (), report | {"status": program.status}
    if spec.return_type not in {"int", "bool"} or any(kind != "int" for _, kind in spec.parameters):
        return (), report | {"status": "UNSUPPORTED_PROJECTION"}
    item = next(row for row in program.functions if row.function.name == spec.function)
    graph = item.flow.graph
    kinds = {block.kind for block in graph.blocks if block.id in item.reachable}
    deadline = program.deadline
    category = None
    try:
        if "loop_header" in kinds:
            report["mode"] = "loops"
            if not enabled & {"normalization", "variable_steps", "mixed_updates"}:
                return (), report | {"status": "COMPONENT_DISABLED"}
            projector = ScalarProjection(context, program)
            loop = build_loop(projector, item, variable="variable_steps" in enabled, mixed="mixed_updates" in enabled)
            changes = tuple(projector.changes.values())
            category = "GENERALIZED_LOOP_CONSTRAINT"
            report["loop_summary"] = loop.source
            def sample(args, edits):
                return loop_value(loop, args, edits, deadline)
        elif "branch" in kinds and "cross_branch" in enabled:
            report["mode"] = "branches"
            projector = ScalarProjection(context, program)
            tree, sites = branches(projector, item)
            changes = tuple(projector.changes.values())
            category = "CROSS_BRANCH_COEFFICIENTS"
            def sample(args, edits):
                return branch_value(tree, args, edits)
        elif "runtime" in enabled:
            report["mode"] = "runtime"
            projector = Projector(context, program, links, helpers, frozenset({"arithmetic", "interprocedural"}))
            formula = projector.build(spec.function, len(spec.parameters))
            changes = formula.changes
            category = "RUNTIME_CONSTRAINT"
            def sample(args, edits):
                evaluate = substitution(args, edits, on_fault=localize)
                for obligation in formula.obligations:
                    evaluate(obligation)
                return (evaluate(formula.output),)
        else:
            return (), report | {"status": "COMPONENT_DISABLED"}

        def collect(edits, *, original=False):
            rows = []
            for example in examples:
                if monotonic() >= deadline:
                    raise ProjectionLimit
                try:
                    rows.append(sample(example.args, edits))
                except LocalizedArithmetic as fault:
                    if not original:
                        return None
                    rows.append((fault,))
                except (ArithmeticError, UnsupportedProjection):
                    if original:
                        raise
                    return None
                except ProjectionLimit:
                    if original or monotonic() >= deadline:
                        raise
                    return None
            return rows

        expected = tuple(example.expected_return for example in examples)
        original = collect((), original=True)
        modeled = tuple(row[0] for row in original)
        report["examples"] = len(examples)
        if category == "GENERALIZED_LOOP_CONSTRAINT":
            report["loop_summary"] |= {"steps": [row[2] for row in original], "iterations": [row[1] for row in original],
                                       "exit_states": [list(row[3]) for row in original]}
        elif category == "CROSS_BRANCH_COEFFICIENTS":
            report["branch"] = branch_witness(sites, graph, original)
        elif category == "RUNTIME_CONSTRAINT":
            by_origin = {id(record.node): record.node.span for record in context.nodes}
            failures = [(position, result) for position, result in enumerate(modeled) if isinstance(result, LocalizedArithmetic)]
            if not failures:
                return (), report | {"status": "NO_MODELED_RUNTIME_FAILURE"}
            if len(failures) == len(examples) or any(fault.origin not in by_origin for _, fault in failures):
                return (), report | {"status": "INSUFFICIENT_RUNTIME_CONSTRAINTS"}
            spans = [by_origin[fault.origin] for _, fault in failures]
            report["modeled_faults"] = [
                {"example": position+1, "code": fault.code, "operator": fault.operator, "operands": list(fault.operands),
                 "span": by_origin[fault.origin].to_dict()} for position, fault in failures
            ]
            changes = tuple(change for change in changes if change.action in {"literal", "operation", "drop_offset"}
                            and any(inside(span, change.edit.span) for span in spans))
        if modeled == expected:
            return (), report | {"status": "CONSTRAINTS_ALREADY_AGREE"}

        matches, variants = [], []
        for change in changes:
            if report["single_trials"] >= MAX_SINGLE_TRIALS or monotonic() >= deadline:
                raise ProjectionLimit
            report["single_trials"] += 1
            checked = collect((change,))
            if checked is not None:
                if tuple(row[0] for row in checked) == expected:
                    matches.append((change,))
                if category == "CROSS_BRANCH_COEFFICIENTS":
                    variants.append((change, checked))
        if category == "CROSS_BRANCH_COEFFICIENTS":
            matches = [] if matches else cross_pairs(variants, original, expected, collect, report, deadline)
    except UnsupportedProjection:
        return (), report | {"status": "UNSUPPORTED_PROJECTION"}
    except ProjectionLimit:
        return (), report | {"status": "ANALYSIS_LIMITED"}
    except ArithmeticError:
        return (), report | {"status": "UNSUPPORTED_CHECKED_ARITHMETIC"}

    matches.sort(key=lambda edits: (sum(edit_cost(context, change.edit) for change in edits),
                                   tuple((change.edit.span.start.offset, change.edit.replacement) for change in edits)))
    report["compatible_candidates"] = len(matches)
    report["status"] = ("MULTIPLE_COMPATIBLE_EDITS" if len(matches) > 1 else
                        "COMPATIBLE_EDIT" if matches else "NO_COMPATIBLE_EDIT")
    proposals = []
    for edits in matches[:MAX_PROPOSALS]:
        evidence = tuple(Evidence("FINITE_CONSTRAINT_WITNESS",
                                 f"The complete edit fits all {len(examples)} trusted examples in the static model.",
                                 change.edit.span) for change in edits)
        proposals.append(Proposal(tuple(change.edit for change in edits), category, evidence,
                                  "Verify this candidate against the supplied expectations before approval.",
                                  "ScalarExpression", "value", type_match=True,
                                  counter_evidence=(Evidence("FINITE_DOMAIN", "Behavior beyond the supplied inputs is unknown.",
                                                             edits[0].edit.span),)))
    return tuple(proposals), report
