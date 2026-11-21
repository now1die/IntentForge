"""Bounded disjunctive reaching definitions and atomic branch facts for Mini-C."""
from collections import deque
from dataclasses import dataclass
from operator import eq, ge, gt, le, lt, ne
from time import monotonic

from compiler import ast_nodes as ast

from .control_flow import Edge
from .dataflow import Definition, MAX_SLICE
from .expression_normalization import INT_MAX, INT_MIN, NEGATE, normalized_comparison

MAX_STATES_PER_BLOCK = 8
MAX_PATH_TRANSFERS = 1_200
MAX_EXCLUSIONS = 6
COMPARE = {"<": lt, "<=": le, ">": gt, ">=": ge, "==": eq, "!=": ne}


@dataclass(frozen=True, order=True, slots=True)
class Range:
    minimum: int = INT_MIN
    maximum: int = INT_MAX
    excluded: tuple[int, ...] = ()

    def restrict(self, op, value):
        lo, hi = self.minimum, self.maximum
        if op in {"<", "<=", "=="}:
            hi = min(hi, value - (op == "<"))
        if op in {">", ">=", "=="}:
            lo = max(lo, value + (op == ">"))
        excluded = {x for x in self.excluded if lo <= x <= hi}
        if op == "!=" and lo <= value <= hi:
            excluded.add(value)
        if hi - lo + 1 <= len(excluded):
            return None
        # Dropping excess exclusions is a conservative widening.
        return Range(lo, hi, tuple(sorted(excluded)[:MAX_EXCLUSIONS]))


@dataclass(frozen=True, order=True, slots=True)
class State:
    facts: tuple[tuple[str, Range], ...] = ()
    definitions: tuple[Definition, ...] = ()


@dataclass(slots=True)
class Paths:
    incoming: list[set[State]]
    complete: bool
    transfers: int
    unresolved: set[int]
    edges: set[Edge]


def predicate(expression, context, bindings):
    if isinstance(expression, ast.Literal) and type(expression.value) is bool:
        return expression.value
    if isinstance(expression, ast.Identifier):
        symbol = bindings.identifiers.get(id(expression))
        if symbol and symbol.type.display() == "bool":
            return (symbol.id, "==", 1, Range(0, 1))
    comparison = normalized_comparison(expression, context.semantic.expression_types, bindings.identifiers)
    if comparison and isinstance(comparison.right, ast.Literal):
        if isinstance(comparison.left, ast.Literal):
            return COMPARE[comparison.operator](comparison.left.value, comparison.right.value)
        symbol = bindings.identifiers.get(id(comparison.left))
        if symbol:
            return (symbol.id, comparison.operator, comparison.right.value, Range())
    return None


def propagate(facts, condition, truth):
    if type(condition) is bool:
        return facts if condition == truth else None
    if condition is None:
        return facts
    binding, operator, value, default = condition
    narrowed = facts.get(binding, default).restrict(operator if truth else NEGATE[operator], value)
    if narrowed is None:
        return None
    return {**facts, binding: narrowed}


def analyze_paths(context, item, bindings, deadline):
    graph, flow = item.flow.graph, item.flow
    outgoing = graph.outgoing()
    incoming = [set() for _ in graph.blocks]
    # Reuse the Phase 6 ownership rules for initial unknown definitions.
    seeds = bindings.globals | {binding for node in [
        *item.function.parameters,
        *(block.syntax for block in graph.blocks if isinstance(block.syntax, (ast.VariableDeclaration, ast.ArrayDeclaration))),
    ] if (binding := bindings.declaration(node))}
    start = State(definitions=tuple(Definition(graph.entry, binding) for binding in sorted(seeds)))
    incoming[graph.entry].add(start)
    pending = deque([(graph.entry, start)])
    predicates = {block.id: predicate(block.expression, context, bindings) for block in graph.blocks
                  if block.kind in {"branch", "loop_header"} and block.expression is not None}
    unresolved, feasible = set(), set()
    transfers = 0
    while pending:
        if transfers >= MAX_PATH_TRANSFERS or monotonic() >= deadline:
            return Paths(incoming, False, transfers, unresolved, feasible)
        site, state = pending.popleft()
        transfers += 1
        effects = flow.effects[site]
        facts = {binding: bound for binding, bound in state.facts if binding not in effects.writes}
        definitions = {item for item in state.definitions if item.binding not in effects.definite}
        definitions.update(Definition(site, binding) for binding in effects.writes)
        defs = tuple(sorted(definitions))
        condition = predicates.get(site)
        if site in predicates and condition is None:
            unresolved.add(site)
        for edge in outgoing[site]:
            next_facts = propagate(facts, condition, edge.kind == "true") if edge.kind in {"true", "false"} else facts
            if next_facts is None:
                continue
            feasible.add(edge)
            proposal = State(tuple(sorted(next_facts.items())), defs)
            states = incoming[edge.target]
            if proposal in states:
                continue
            if len(states) >= MAX_STATES_PER_BLOCK:
                return Paths(incoming, False, transfers, unresolved, feasible)
            states.add(proposal)
            pending.append((edge.target, proposal))
    return Paths(incoming, flow.complete, transfers, unresolved, feasible)


def value_slice(flow, direct, deadline):
    pending, known = list(reversed(direct)), set()
    while pending:
        if len(known) >= MAX_SLICE or monotonic() >= deadline:
            return sorted(known), False
        row = pending.pop()
        if row in known:
            continue
        known.add(row)
        if row.site != flow.graph.entry:
            for binding in sorted(flow.effects[row.site].reads):
                pending.extend(reversed(sorted(flow.use_defs(row.site, binding) - known)))
    return sorted(known), flow.complete


def return_paths(item, paths, bindings, deadline):
    flow = item.flow
    rows = []
    returns = sorted((block for block in flow.graph.blocks if block.kind == "return"),
                     key=lambda block: block.syntax.span.start.offset)
    for block in returns:
        effect = flow.effects[block.id]
        reads = effect.reads
        local = {Definition(block.id, binding) for binding in effect.writes & reads}
        states = sorted(paths.incoming[block.id])
        def describe(definition):
            return {"binding": definition.binding, "name": bindings.symbols[definition.binding].name,
                    "site": definition.site, "span": flow.graph.blocks[definition.site].syntax.span.to_dict()}

        results = []
        for state in states:
            direct = [row for row in sorted(set(state.definitions) | local) if row.binding in reads]
            dependencies, complete = value_slice(flow, direct, deadline)
            results.append({
                "facts": [{"binding": binding, "name": bindings.symbols[binding].name, "min": bound.minimum,
                           "max": bound.maximum, "excluded": list(bound.excluded)} for binding, bound in state.facts],
                "definitions": [describe(row) for row in direct],
                "possible_upstream_definitions": [describe(row) for row in dependencies if row not in direct],
                "dependencies_complete": paths.complete and complete,
            })
        rows.append({
            "site": block.id, "span": block.syntax.span.to_dict(),
            "feasibility": "modeled" if states else "excluded" if paths.complete else "unknown",
            "paths": results,
        })
    return rows
