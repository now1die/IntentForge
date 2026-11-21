"""Reusable bounded Mini-C function and dependency summaries."""
from dataclasses import dataclass
from time import monotonic

from compiler import ast_nodes as ast

from .control_flow import FlowLimit, build_graph
from .dataflow import BindingIndex, Reaching, reaching_definitions
from .expression_normalization import normalized_comparison

MAX_AST = 1_200
MAX_FUNCTIONS = 16
MAX_PROGRAM_BLOCKS = 450
MAX_SECONDS = .35


@dataclass(slots=True)
class FunctionFlow:
    function: ast.FunctionDefinition
    flow: Reaching
    reachable: set[int]

    def direct_calls(self):
        return frozenset(call for site in self.reachable for call in self.flow.effects[site].calls)


@dataclass(slots=True)
class ProgramFlow:
    bindings: BindingIndex | None
    functions: tuple[FunctionFlow, ...]
    status: str
    deadline: float


def analyze_program(context, deadline):
    bounded_deadline = min(deadline, monotonic() + MAX_SECONDS)
    if not context.compiler_valid:
        return ProgramFlow(None, (), "INCOMPLETE_COMPILER_EVIDENCE", bounded_deadline)
    if len(context.nodes) > MAX_AST:
        return ProgramFlow(None, (), "ANALYSIS_LIMITED", bounded_deadline)
    bindings = BindingIndex.from_context(context)
    functions = []
    count = 0
    complete = True
    for function in context.parsed.ast.functions:
        if len(functions) >= MAX_FUNCTIONS or monotonic() >= bounded_deadline:
            complete = False
            break
        try:
            graph = build_graph(function)
        except (FlowLimit, RecursionError):
            complete = False
            continue
        count += len(graph.blocks)
        if count > MAX_PROGRAM_BLOCKS:
            complete = False
            break
        definitions = reaching_definitions(graph, function, bindings, bounded_deadline)
        functions.append(FunctionFlow(function, definitions, graph.reachable()))
        complete &= definitions.complete
    return ProgramFlow(bindings, tuple(functions), "AVAILABLE" if complete else "ANALYSIS_LIMITED", bounded_deadline)


def recursive_relation(name, call_graph):
    seen, pending = set(), list(call_graph[name] - {name})
    mutual = False
    while pending:
        current = pending.pop()
        if current == name:
            mutual = True
        elif current in call_graph and current not in seen:
            seen.add(current)
            pending.extend(call_graph[current] - seen)
    direct = name in call_graph[name]
    return "DIRECT_AND_MUTUAL" if direct and mutual else "DIRECT" if direct else "MUTUAL" if mutual else "NONE"


def summaries(context, analysis, *, include_graph=False):
    call_graph = {item.function.name: item.direct_calls() for item in analysis.functions}
    result = []
    bindings = analysis.bindings
    for item in analysis.functions:
        function, flow = item.function, item.flow
        graph = flow.graph
        returns = []
        conditions = []
        complete = flow.complete
        writes = set()
        possible = set()
        for block in graph.blocks:
            if block.id not in item.reachable:
                continue
            effects = flow.effects[block.id]
            writes.update(effects.definite)
            possible.update(effects.writes - effects.definite)
            if block.kind in {"branch", "loop_header"} and block.expression is not None:
                normalized = normalized_comparison(block.expression, context.semantic.expression_types, bindings.identifiers)
                conditions.append({"span": block.expression.span.to_dict(), "kind": block.kind,
                                   "reads": sorted(effects.reads),
                                   "normalized": [context.text(normalized.left.span), normalized.operator,
                                                  context.text(normalized.right.span)] if normalized else None})
            if block.kind == "return":
                traced, finished = flow.return_slice(block.id, analysis.deadline)
                complete &= finished
                returns.append({
                    "span": block.syntax.span.to_dict(), "reads": sorted(effects.reads),
                    "definitions": [{"binding": row.binding, "name": bindings.symbols[row.binding].name,
                                     "site": row.site, "span": graph.blocks[row.site].syntax.span.to_dict()}
                                    for row in traced],
                    "complete": finished,
                })
        fallthrough = any(edge.target == graph.exit and edge.kind != "return" and edge.source in item.reachable
                          for edge in graph.edges)
        types = {function.return_type, *(parameter.type_name for parameter in function.parameters)}
        types.update(getattr(block.syntax, "type_name", "void") for block in graph.blocks)
        effects = []
        if any(flow.effects[site].array_access for site in item.reachable):
            effects.append("array_cells_merged")
        if item.direct_calls():
            effects.append("call_effects_over_approximate_globals")
        if types - {"int", "bool", "void"}:
            effects.append("vm_support_not_established")
        result.append({
            "name": function.name, "parameters": [{"name": parameter.name, "type": parameter.type_name} for parameter in function.parameters],
            "return_type": function.return_type, "calls": sorted(item.direct_calls()),
            "recursion": recursive_relation(function.name, call_graph),
            "conditions": conditions, "returns": returns,
            "direct_writes": sorted(writes), "possible_writes": sorted(possible),
            "effects": effects, "possible_missing_return": fallthrough and function.return_type != "void",
            "blocks": len(graph.blocks), "edges": len(graph.edges), "reachable_blocks": len(item.reachable),
            "complete": complete,
            **({"cfg": graph.to_dict()} if include_graph else {}),
        })
    status = analysis.status if all(row["complete"] for row in result) else "ANALYSIS_LIMITED"
    return {"status": status, "functions": result}
