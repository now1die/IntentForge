"""Finite branch constraints, coordinated coefficients and bounded loop summaries."""
from dataclasses import dataclass
from itertools import combinations, product
from time import monotonic

from compiler import ast_nodes as ast
from compiler.source_location import SourceSpan

from .intention_candidates import Evidence, Proposal
from .intention_phase8 import (
    COMPARISONS, MAX_DEPTH, MAX_NODES, Change, Projector, ProjectionLimit, Term,
    UnsupportedProjection, edit_cost, project_changes, signed, substitution,
)

COMPONENTS = frozenset({"branches", "coordinated", "loops"})
CATEGORIES = frozenset({
    "BRANCH_ARITHMETIC_CONSTRAINT", "BRANCH_BOUNDARY_MISMATCH", "BOOLEAN_INTERVAL_CONSTRAINT",
    "COORDINATED_COEFFICIENTS", "LOOP_COUNT_CONSTRAINT",
})
BOUNDARY_ALTERNATES = {"<": "<=", "<=": "<", ">": ">=", ">=": ">", "==": "!=", "!=": "=="}
MAX_PATHS = 8
MAX_BLOCK_VISITS = 64
MAX_SINGLE_TRIALS = 96
MAX_PAIR_TRIALS = 96
MAX_PAIR_SITES = 8
MAX_LOOP_POINTS = 64
MAX_PROPOSALS = 4


@dataclass(frozen=True, slots=True)
class Path:
    obligations: tuple
    term: Term
    site: int
    branches: tuple = ()
    definitions: tuple = ()


@dataclass(frozen=True, slots=True)
class Loop:
    initial: Term
    limit: Term
    seed: Term
    predicate: Term
    increment: Term
    comparison: Term
    step: Term
    header: SourceSpan
    update: SourceSpan
    return_span: SourceSpan
    seed_span: SourceSpan
    count_span: SourceSpan
    predicate_span: SourceSpan | None


class ScalarProjection(Projector):
    """Translate pure scalar operations using the compiler's lexical bindings."""

    def __init__(self, context, program):
        super().__init__(context, program, {}, {}, frozenset({"arithmetic"}))

    def identifier(self, node):
        if isinstance(node, ast.Identifier):
            symbol = self.bindings.identifiers.get(id(node))
            return symbol.id if symbol and symbol.type.display() == "int" else None
        return None

    def operator_span(self, node):
        return next((token.span for token in self.context.parsed.tokens
                     if node.left.span.end.offset <= token.span.start.offset < node.right.span.start.offset
                     and token.lexeme == node.operator), None)

    def boolean(self, node, locals_, depth=0):
        self.visits += 1
        if self.visits > MAX_NODES or depth > MAX_DEPTH or monotonic() >= self.deadline:
            raise ProjectionLimit
        if isinstance(node, ast.Literal) and type(node.value) is bool:
            return Term("literal", value=node.value)
        if isinstance(node, ast.UnaryExpression) and node.operator == "!":
            return Term("!", (self.boolean(node.operand, locals_, depth + 1),))
        if isinstance(node, ast.BinaryExpression) and node.operator in {"&&", "||"}:
            left, right = (self.boolean(child, locals_, depth + 1) for child in (node.left, node.right))
            alternate = "||" if node.operator == "&&" else "&&"
            replacement = f"(({self.context.text(node.left.span)}) {alternate} ({self.context.text(node.right.span)}))"
            self.change(node, node.span, replacement, "BOOLEAN_INTERVAL_CONSTRAINT", "operation", alternate)
            return Term(node.operator, (left, right), origin=id(node))
        if isinstance(node, ast.BinaryExpression) and node.operator in COMPARISONS:
            left, right = (self.expression(child, locals_, 0, depth + 1) for child in (node.left, node.right))
            self.comparison_change(node)
            if node.operator in {"<", "<=", ">", ">="}:
                self.change(node, node.span,
                            f"(({self.context.text(node.right.span)}) {node.operator} ({self.context.text(node.left.span)}))",
                            "BRANCH_BOUNDARY_MISMATCH", "swap", node.operator)
            return Term(node.operator, (left, right), origin=id(node))
        raise UnsupportedProjection

    def comparison_change(self, node):
        span = self.operator_span(node)
        if span:
            alternate = BOUNDARY_ALTERNATES[node.operator]
            self.change(node, span, alternate, "BRANCH_BOUNDARY_MISMATCH", "operation", alternate)

    def entry_locals(self, item):
        return {self.bindings.declaration(param): Term("parameter", value=i)
                for i, param in enumerate(item.function.parameters)}


def branches(projector, item):
    graph = item.flow.graph
    outgoing = graph.outgoing()
    visits = paths = 0
    sites = {}

    def walk(site, locals_, definitions, obligations):
        nonlocal visits, paths
        visits += 1
        if visits > MAX_BLOCK_VISITS or monotonic() >= projector.deadline:
            raise ProjectionLimit
        block = graph.blocks[site]
        node = block.syntax
        edges = outgoing[site]
        if block.kind == "return" and block.expression is not None:
            paths += 1
            if paths > MAX_PATHS:
                raise ProjectionLimit
            output = (projector.boolean(block.expression, locals_) if item.function.return_type == "bool"
                      else projector.expression(block.expression, locals_, 0))
            reaching = tuple((projector.bindings.symbols[binding].name, definition)
                             for binding, definition in sorted(definitions.items())
                             if binding in item.flow.effects[site].reads)
            return Path(obligations, output, site, definitions=reaching)
        if block.kind == "branch":
            guard = projector.boolean(block.expression, locals_)
            sites[site] = {"site": site, "span": block.expression.span.to_dict(),
                           "predicate": projector.context.text(block.expression.span),
                           "edges": [edge.kind for edge in edges]}
            children = tuple((edge.kind, walk(edge.target, locals_, definitions, ())) for edge in edges)
            return Path(obligations, guard, site, branches=children)
        if len(edges) != 1 or edges[0].kind != "next" or block.kind not in {"entry", "statement"}:
            raise UnsupportedProjection
        if block.kind == "entry":
            return walk(edges[0].target, locals_, definitions, obligations)
        if isinstance(node, ast.VariableDeclaration) and node.type_name == "int" and node.initializer is not None:
            binding = projector.bindings.declaration(node)
            value = projector.expression(node.initializer, locals_, 0)
        else:
            assignment = node.expression if isinstance(node, ast.ExpressionStatement) else node
            if not isinstance(assignment, ast.Assignment) or assignment.operator not in {"=", "+=", "-="}:
                raise UnsupportedProjection
            binding = projector.identifier(assignment.target)
            if binding not in locals_:
                raise UnsupportedProjection
            value = projector.expression(assignment.value, locals_, 0)
            if assignment.operator != "=":
                value = Term(assignment.operator[0], (locals_[binding], value))
        if binding is None:
            raise UnsupportedProjection
        return walk(edges[0].target, {**locals_, binding: value}, {**definitions, binding: site}, (*obligations, value))

    root = walk(graph.entry, projector.entry_locals(item), {}, ())
    if not sites and item.function.return_type != "bool":
        raise UnsupportedProjection
    return root, sorted(sites.values(), key=lambda row: row["span"]["start"]["offset"])


def branch_value(root, args, changes):
    evaluate = substitution(args, changes)
    edges = []
    path = root
    while True:
        for term in path.obligations:
            evaluate(term)
        value = evaluate(path.term)
        if not path.branches:
            return value, path, tuple(edges)
        truth = "true" if value else "false"
        edges.append((path.site, truth))
        path = next((child for label, child in path.branches if label == truth), None)
        if path is None:
            raise ArithmeticError("The branch is outside the projected CFG")


def single_statement(node):
    if isinstance(node, ast.Block) and len(node.statements) == 1:
        return node.statements[0]
    return node


def loop_summary(projector, item):
    statements = item.function.body.statements
    if len(statements) != 3:
        raise UnsupportedProjection
    seed, loop, tail = statements
    if (not isinstance(seed, ast.VariableDeclaration) or seed.type_name != "int" or seed.initializer is None
            or not isinstance(loop, ast.ForStatement) or not isinstance(tail, ast.ReturnStatement)):
        raise UnsupportedProjection
    graph = item.flow.graph
    header = next((block for block in graph.blocks if block.kind == "loop_header" and block.syntax is loop), None)
    if header is None or not any(edge.kind == "back" and edge.target == header.id for edge in graph.edges):
        raise UnsupportedProjection
    initial, guard, update = loop.initializer, loop.condition, loop.update
    if (not isinstance(initial, ast.VariableDeclaration) or initial.type_name != "int" or initial.initializer is None
            or not isinstance(guard, ast.BinaryExpression) or guard.operator not in {"<", "<=", ">", ">="}):
        raise UnsupportedProjection
    index = projector.bindings.declaration(initial)
    accumulator = projector.bindings.declaration(seed)
    if (index is None or accumulator is None or projector.identifier(guard.left) != index
            or projector.identifier(tail.value) != accumulator):
        raise UnsupportedProjection
    if isinstance(update, ast.UpdateExpression) and projector.identifier(update.operand) == index:
        step = 1 if update.operator == "++" else -1
        step_term = Term("literal", value=step)
    elif (isinstance(update, ast.Assignment) and update.operator in {"+=", "-="}
          and projector.identifier(update.target) == index and isinstance(update.value, ast.Literal)
          and type(update.value.value) is int and 1 <= update.value.value <= MAX_LOOP_POINTS):
        step = update.value.value * (1 if update.operator == "+=" else -1)
        magnitude = projector.expression(update.value, {}, 0)
        step_term = magnitude if step > 0 else Term("negate", (magnitude,))
    else:
        raise UnsupportedProjection
    if (step > 0) != (guard.operator in {"<", "<="}):
        raise UnsupportedProjection

    body = single_statement(loop.body)
    predicate = Term("literal", value=True)
    locals_ = projector.entry_locals(item)
    initial_term = projector.expression(initial.initializer, locals_, 0)
    limit = projector.expression(guard.right, locals_, 0)
    seed_term = projector.expression(seed.initializer, locals_, 0)
    projector.comparison_change(guard)
    predicate_span = None
    if isinstance(body, ast.IfStatement):
        if body.else_branch is not None:
            raise UnsupportedProjection
        predicate = projector.boolean(body.condition, {**locals_, index: Term("parameter", value=len(locals_))})
        predicate_span = body.condition.span
        body = single_statement(body.then_branch)
    assignment = body.expression if isinstance(body, ast.ExpressionStatement) else body
    if isinstance(assignment, ast.UpdateExpression) and projector.identifier(assignment.operand) == accumulator:
        increment = Term("literal", value=1 if assignment.operator == "++" else -1)
    elif (isinstance(assignment, ast.Assignment) and assignment.operator in {"+=", "-="}
          and projector.identifier(assignment.target) == accumulator and isinstance(assignment.value, ast.Literal)
          and type(assignment.value.value) is int):
        increment = projector.expression(assignment.value, {}, 0)
        if assignment.operator == "-=":
            increment = Term("negate", (increment,))
    else:
        raise UnsupportedProjection
    comparison = Term(guard.operator, (Term("parameter", value=0), Term("parameter", value=1)), origin=id(guard))
    return Loop(initial_term, limit, seed_term, predicate, increment, comparison, step_term,
                guard.span, update.span, tail.span, seed.span, assignment.span, predicate_span)


def count_value(loop, args, changes):
    evaluate = substitution(args, changes)
    first, bound, seed, step = (evaluate(term) for term in (loop.initial, loop.limit, loop.seed, loop.step))
    direction = 1 if loop.comparison.operation in {"<", "<="} else -1
    if not 1 <= step * direction <= MAX_LOOP_POINTS:
        raise ArithmeticError("The induction step is outside the modeled direction or range")
    distance = (bound - first) * direction
    inclusive = substitution((bound, bound), changes)(loop.comparison)
    size = max(0, (distance + inclusive + abs(step) - 1) // abs(step))
    if size > MAX_LOOP_POINTS:
        raise ProjectionLimit
    # The latch runs even when the next guard will exit.
    end = signed(first + size * step)
    matches = sum(bool(substitution((*args, index), changes)(loop.predicate))
                  for index in range(first, end, step))
    output = signed(seed + matches * evaluate(loop.increment)) if matches else seed
    return output, size, matches, step


def influences(original, observed):
    return tuple(after - before for before, after in zip(original, observed, strict=True))


def independent(left, right):
    return any(left[i] * right[j] != left[j] * right[i] for i, j in combinations(range(len(left)), 2))


def paired_coefficients(formula, evaluate, original, expected, report, deadline):
    if len(original) < 3 or sum(a != b for a, b in zip(original, expected, strict=True)) < 2:
        return []
    groups = {}
    for change in formula.changes:
        if report["single_trials"] >= MAX_SINGLE_TRIALS or monotonic() >= deadline:
            raise ProjectionLimit
        report["single_trials"] += 1
        values = evaluate((change,))
        if values == expected:
            return []
        if change.action != "literal" or (len(groups) >= MAX_PAIR_SITES and change.origin not in groups):
            continue
        if values is None or values == original:
            continue
        groups.setdefault(change.origin, []).append((change, influences(original, values)))
    results = []
    for left, right in combinations(groups.values(), 2):
        for (a, effect_a), (b, effect_b) in product(left, right):
            if report["pair_trials"] >= MAX_PAIR_TRIALS or monotonic() >= deadline:
                raise ProjectionLimit
            if not independent(effect_a, effect_b):
                continue
            if a.edit.span.start.offset > b.edit.span.start.offset:
                a, b = b, a
            if a.edit.span.end.offset > b.edit.span.start.offset:
                continue
            report["pair_trials"] += 1
            if evaluate((a, b)) == expected:
                results.append((a, b))
    return results


def branch_witness(sites, graph, samples):
    counts = {(site["site"], edge): 0 for site in sites for edge in site["edges"]}
    exits = {}
    for _, path, edges in samples:
        for edge in edges:
            counts[edge] += 1
        key = (path.site, edges, path.definitions)
        exits[key] = exits.get(key, 0) + 1
    return {
        "guards": [{**site, "supplied_coverage": {label: counts[site["site"], label] for label in site["edges"]}}
                   for site in sites],
        "returns": [{"site": site, "span": graph.blocks[site].syntax.span.to_dict(),
                     "expression_span": graph.blocks[site].expression.span.to_dict(),
                     "conditions": [{"site": guard, "outcome": edge} for guard, edge in edges],
                     "definitions": [{"name": name, "site": definition,
                                      "span": graph.blocks[definition].syntax.span.to_dict()}
                                     for name, definition in definitions], "examples": count}
                    for (site, edges, definitions), count in sorted(exits.items())],
    }


def loop_witness(loop, samples):
    return {"guard_span": loop.header.to_dict(), "update_span": loop.update.to_dict(),
            "seed_span": loop.seed_span.to_dict(), "accumulator_update_span": loop.count_span.to_dict(),
            "predicate_span": loop.predicate_span.to_dict() if loop.predicate_span else None,
            "return_span": loop.return_span.to_dict(),
            "step": samples[0][3], "point_limit": MAX_LOOP_POINTS,
            "iterations": [size for _, size, _, _ in samples], "matches": [matches for _, _, matches, _ in samples]}


def synthesize(context, program, links, helpers, specification, enabled):
    report = {"status": "INCOMPLETE_SPECIFICATION", "components": sorted(enabled), "single_trials": 0,
              "pair_trials": 0, "compatible_candidates": 0, "scope": "SUPPLIED_EXAMPLES_ONLY"}
    examples = specification.examples
    if not enabled:
        return (), report | {"status": "SPECIFICATION_ONLY"}
    if len({example.args for example in examples}) < 2:
        return (), report
    if program.status != "AVAILABLE":
        return (), report | {"status": program.status}
    if specification.return_type not in {"int", "bool"} or any(kind != "int" for _, kind in specification.parameters):
        return (), report | {"status": "UNSUPPORTED_PROJECTION"}
    item = next(row for row in program.functions if row.function.name == specification.function)
    kinds = {block.kind for block in item.flow.graph.blocks if block.id in item.reachable}
    conditional = "branch" in kinds or specification.return_type == "bool"
    mode = "loops" if "loop_header" in kinds else "branches" if conditional else "coordinated"
    if mode not in enabled:
        return (), report | {"status": "COMPONENT_DISABLED", "mode": mode}
    report["mode"] = mode
    try:
        if mode == "coordinated":
            formula = Projector(context, program, links, helpers, frozenset({"arithmetic", "interprocedural"})).build(
                specification.function, len(specification.parameters))
            def sample(args, changes):
                return (project_changes(formula, args, changes),)
        else:
            projector = ScalarProjection(context, program)
            if mode == "branches":
                tree, sites = branches(projector, item)
                def sample(args, changes):
                    return branch_value(tree, args, changes)
            else:
                loop = loop_summary(projector, item)
                def sample(args, changes):
                    return count_value(loop, args, changes)

        def collect(changes):
            rows = []
            for example in examples:
                if monotonic() >= program.deadline:
                    raise ProjectionLimit
                rows.append(sample(example.args, changes))
            return rows

        def evaluate(changes):
            try:
                values = tuple(row[0] for row in collect(changes))
                return values if None not in values else None
            except (ArithmeticError, ProjectionLimit):
                return None

        expected = tuple(example.expected_return for example in examples)
        samples = collect(())
        original = tuple(row[0] for row in samples)
        if None in original:
            raise ArithmeticError
        if mode == "branches":
            report["branch"] = branch_witness(sites, item.flow.graph, samples)
        elif mode == "loops":
            report["loop"] = loop_witness(loop, samples)
        report["examples"] = len(examples)
        report["original_mismatches"] = sum(actual != want for actual, want in zip(original, expected, strict=True))
        if original == expected:
            return (), report | {"status": "CONSTRAINTS_ALREADY_AGREE"}
        if mode == "coordinated":
            matches = paired_coefficients(formula, evaluate, original, expected, report, program.deadline)
        else:
            matches = []
            for change in projector.changes.values():
                if report["single_trials"] >= MAX_SINGLE_TRIALS or monotonic() >= program.deadline:
                    raise ProjectionLimit
                report["single_trials"] += 1
                if evaluate((change,)) == expected:
                    matches.append((change,))
    except UnsupportedProjection:
        return (), report | {"status": "UNSUPPORTED_PROJECTION"}
    except ProjectionLimit:
        return (), report | {"status": "ANALYSIS_LIMITED"}
    except ArithmeticError:
        return (), report | {"status": "UNSUPPORTED_CHECKED_ARITHMETIC"}

    def order(changes):
        return (sum(edit_cost(context, change.edit) for change in changes),
                tuple((change.edit.span.start.offset, change.edit.replacement) for change in changes))

    matches.sort(key=order)
    report["compatible_candidates"] = len(matches)
    report["status"] = ("MULTIPLE_COMPATIBLE_EDITS" if len(matches) > 1 else
                        "COMPATIBLE_EDIT" if matches else "NO_COMPATIBLE_EDIT")
    report["witnesses"] = []
    proposals = []
    for changes in matches[:MAX_PROPOSALS]:
        try:
            witnesses = collect(changes)
        except ProjectionLimit:
            return (), report | {"status": "ANALYSIS_LIMITED", "witnesses": []}
        category = {"loops": "LOOP_COUNT_CONSTRAINT", "coordinated": "COORDINATED_COEFFICIENTS"}.get(
            mode, changes[0].category if changes[0].category in CATEGORIES else "BRANCH_ARITHMETIC_CONSTRAINT")
        evidence = tuple(Evidence("FINITE_CONSTRAINT_WITNESS",
                                  f"The complete repair agrees with all {len(examples)} supplied expectations in the {mode} model.",
                                  change.edit.span) for change in changes)
        proposals.append(Proposal(tuple(change.edit for change in changes), category, evidence,
                                  "Review the complete edit together with isolated test evidence.", "ScalarExpression", "value",
                                  type_match=True, counter_evidence=(Evidence(
                                      "FINITE_DOMAIN", "Other edits or unsampled inputs may have different behavior.",
                                      changes[0].edit.span),)))
        report["witnesses"].append({
            "edits": [{"span": change.edit.span.to_dict(), "replacement": change.edit.replacement} for change in changes],
            **({"branch": branch_witness(sites, item.flow.graph, witnesses)} if mode == "branches" else {}),
            **({"loop": loop_witness(loop, witnesses)} if mode == "loops" else {}),
        })
    return tuple(proposals), report
