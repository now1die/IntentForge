"""Phase 6.5 path evidence, precision gates and review-only recursive repairs."""
from itertools import islice
from time import monotonic

from analysis_evidence.expression_normalization import normalized_comparison
from analysis_evidence.interprocedural import atom, contracts, descendants, scalar_helpers
from analysis_evidence.path_flow import analyze_paths, return_paths
from analysis_evidence.recursive_layout import guarded_layout
from compiler import ast_nodes as ast
from compiler.symbol_table import SymbolKind

from .intention_candidates import Edit, Evidence, Proposal
from .intention_phase6 import MATH, computed_chain, guarded_return

COMPONENTS = frozenset({"precision", "recursion", "recurrence"})
MAX_NEW = 6


def simple_recurrence(context, item, bindings, path, semantic_layout, helpers):
    function = item.function
    statements = function.body.statements
    if not 1 <= len(function.parameters) <= 4:
        return None
    if semantic_layout:
        branches = [block for block in item.flow.graph.blocks if block.kind == "branch" and path.incoming[block.id]]
        if len(branches) != 1:
            return None
        condition = normalized_comparison(branches[0].expression, context.semantic.expression_types, bindings.identifiers)
        layout = guarded_layout(item, path, bindings, condition) if condition else None
        if layout is None:
            return None
        branch, base, fallback, condition = layout
    else:
        if len(statements) != 2:
            return None
        branch, fallback = statements
        if not isinstance(branch, ast.IfStatement) or branch.else_branch is not None or not isinstance(fallback, ast.ReturnStatement):
            return None
        base = guarded_return(branch.then_branch)
        condition = normalized_comparison(branch.condition, context.semantic.expression_types, bindings.identifiers)
    if fallback.value is None:
        return None
    if not base or base.value is None or any(
            not isinstance(node, (ast.Literal, ast.Identifier, ast.BinaryExpression))
            or isinstance(node, ast.BinaryExpression) and node.operator not in MATH
            for node in descendants(base.value)):
        return None
    if not condition or not isinstance(condition.left, ast.Identifier) or not isinstance(condition.right, ast.Literal):
        return None
    guard_binding = bindings.identifiers.get(id(condition.left))
    if not guard_binding:
        return None
    position = next((i for i, parameter in enumerate(function.parameters)
                     if bindings.declaration(parameter) == guard_binding.id), None)
    if position is None:
        return None
    parts = tuple(descendants(fallback.value))
    all_calls = tuple(node for node in parts if isinstance(node, ast.FunctionCall))
    if any(not isinstance(call.callee, ast.Identifier) or
           call.callee.name != function.name and call.callee.name not in helpers for call in all_calls):
        return None
    calls = tuple(call for call in all_calls if call.callee.name == function.name)
    if (not calls or any(not isinstance(node, (ast.FunctionCall, ast.BinaryExpression, ast.Identifier, ast.Literal))
                        or isinstance(node, ast.BinaryExpression) and node.operator not in MATH for node in parts)):
        return None
    if any(len(call.arguments) != len(function.parameters) for call in calls):
        return None
    if any(not isinstance(node, (ast.BinaryExpression, ast.Identifier, ast.Literal))
           for call in calls for arg in call.arguments for node in descendants(arg)):
        return None
    return branch, base, fallback, condition, guard_binding, position, calls


def recursive_candidates(context, item, bindings, path, examples, enabled, helpers):
    studied = simple_recurrence(context, item, bindings, path, "layout" in enabled, helpers)
    if studied is None:
        return
    branch, base, fallback, condition, binding, position, calls = studied
    reachable_returns = {id(block.syntax) for block in item.flow.graph.blocks
                         if block.kind == "return" and path.incoming[block.id]}
    if not {id(base), id(fallback)} <= reachable_returns:
        return
    direction = {">": 1, ">=": 1, "<": -1, "<=": -1}.get(condition.operator)
    if direction is None:
        return
    guarded = Evidence("RECURSIVE_GUARD_PARAMETER",
                       f"The guarded base return depends on argument {position + 1} ({binding.name}).", branch.condition.span)
    unknown = Evidence("RECURRENCE_NOT_SPECIFIED", "Other arguments can have independent roles, and the intended domain may be narrower.", branch.span)
    if "recursion" in enabled and len(item.function.parameters) > 1 and len(calls) == 1:
        argument = calls[0].arguments[position]
        relation = atom(argument, bindings)
        if relation and relation[0] == binding.id and relation[2] == 0:
            operator = "+" if direction > 0 else "-"
            yield Proposal((Edit(argument.span, f"{binding.name} {operator} 1"),), "RECURSIVE_PARAMETER_PROGRESS",
                           (guarded, Evidence("UNCHANGED_GUARD_ARGUMENT",
                                              "The self-call passes the guarded binding unchanged while retaining other argument computations.", argument.span)),
                           "Advance this argument one unit toward the guard and leave the remaining argument roles intact.",
                           "FunctionCall", "arguments", type_match=True, counter_evidence=(unknown,))
    if "recurrence" not in enabled or not examples or len(calls) != 2:
        return
    expression = fallback.value
    while isinstance(expression, ast.FunctionCall) and isinstance(expression.callee, ast.Identifier):
        helper = helpers.get(expression.callee.name)
        if not helper or helper["identity_parameter"] != 0 or len(expression.arguments) != 1:
            break
        expression = expression.arguments[0]
    if not isinstance(expression, ast.BinaryExpression) or expression.left is not calls[0] or expression.right is not calls[1]:
        return
    relations = [atom(call.arguments[position], bindings) for call in calls]
    if any(row is None or row[0] != binding.id or not 1 <= row[2]*direction <= 4 for row in relations):
        return
    if relations[0][2] == relations[1][2]:
        return

    def outside_base(example):
        if not typed_arguments(item.function, example.args):
            return False
        value, boundary = example.args[position], condition.right.value
        inside = {"<": value < boundary, "<=": value <= boundary, ">": value > boundary, ">=": value >= boundary}
        return not inside[condition.operator]

    if not any(outside_base(example) for example in examples):
        return
    start, end = expression.left.span.end.offset, expression.right.span.start.offset
    operator_token = next((token for token in context.parsed.tokens if start <= token.span.start.offset < end
                           and token.lexeme == expression.operator), None)
    if operator_token is None:
        return
    for replacement in ("+", "-", "*"):
        if replacement != expression.operator:
            yield Proposal((Edit(operator_token.span, replacement),), "RECURRENCE_OPERATOR_MISMATCH",
                           (guarded, Evidence("TWO_RECURSIVE_TERMS", "The fallback combines distinct guarded self-call offsets.", expression.span),
                            Evidence("SUPPLIED_RECURSIVE_TEST", "A supplied input reaches beyond the initial guard.", expression.span)),
                           "Compare this operator against the supplied examples through isolated verification.",
                           "BinaryExpression", "operator", type_match=True,
                           counter_evidence=(Evidence("ALTERNATIVE_RECURRENCE",
                                                      "Subtraction, addition and multiplication can each be intentional.", expression.span),))


def typed_arguments(function, arguments):
    supported = {"int": int, "bool": bool}
    return len(arguments) == len(function.parameters) and all(type(value) is supported.get(parameter.type_name)
        for value, parameter in zip(arguments, function.parameters, strict=True))


def path_examples(function, bindings, paths, examples, writes):
    positions = {binding: index for index, parameter in enumerate(function.parameters)
                 if (binding := bindings.declaration(parameter)) not in writes}
    for state in sorted(paths):
        if not state.facts or any(binding not in positions for binding, _ in state.facts):
            continue
        for row in examples:
            if typed_arguments(function, row.args) and all(
                    bound.minimum <= row.args[positions[binding]] <= bound.maximum
                    and row.args[positions[binding]] not in bound.excluded for binding, bound in state.facts):
                return True
    return False


def branch_returns(context, item, bindings, paths, examples):
    if not examples or not paths.complete:
        return
    flow = item.flow
    live = [block for block in flow.graph.blocks if paths.incoming[block.id]]
    if any(flow.effects[block.id].calls or flow.effects[block.id].array_access
           or flow.effects[block.id].writes & bindings.globals for block in live):
        return
    returns = [block for block in live if block.kind == "return" and isinstance(block.expression, ast.Identifier)]
    if len(returns) != 2:
        return
    writes = set().union(*(flow.effects[block.id].writes for block in live))
    for site, sibling in (returns, reversed(returns)):
        initial = bindings.identifiers.get(id(site.expression))
        terminal = bindings.identifiers.get(id(sibling.expression))
        if (initial is None or terminal is None or initial.id == terminal.id
                or initial.kind != SymbolKind.VARIABLE or terminal.kind != SymbolKind.VARIABLE
                or initial.type.display() != terminal.type.display() or terminal.id in bindings.globals
                or context.visible_at(site.expression.span.start.offset).get(terminal.name) is not terminal):
            continue
        chain = computed_chain(flow, site.id, terminal.id, initial.id, bindings)
        if not chain or not path_examples(item.function, bindings, paths.incoming[site.id], examples, writes):
            continue
        yield Proposal((Edit(site.expression.span, terminal.name),), "PATH_RETURN_DEPENDENCY",
                       (Evidence("PATH_TEST_DOMAIN", "A supplied input satisfies modeled facts for this earlier return.", site.syntax.span),
                        Evidence("SIBLING_RETURN_DEPENDENCY", "A sibling return uses the terminal computed from this binding.", chain[0].syntax.span)),
                       "Try the sibling result on this path and check both paths against their supplied expectations.",
                       "ReturnStatement", "value", type_match=True,
                       counter_evidence=(Evidence("LEGITIMATE_PATH_RESULT", "The branches may intentionally return different processing stages.", sibling.syntax.span),))


def precise_return(candidate, function_paths):
    if len(candidate.edits) < 2:
        return False
    sets = []
    for edit in candidate.edits:
        found = [row for info in function_paths.values() if info["complete"] for row in info["returns"]
                 if row["span"]["start"]["offset"] <= edit.span.start.offset < row["span"]["end"]["offset"]]
        if len(found) != 1 or not found[0]["paths"]:
            return False
        sets.append({tuple((fact["binding"], fact["min"], fact["max"], tuple(fact["excluded"])) for fact in state["facts"])
                     for state in found[0]["paths"]})
    return all(sets) and all(facts for values in sets for facts in values) and len(sets) == 2 and sets[0].isdisjoint(sets[1])


def recurrence_structure(context, item, path):
    name = item.function.name
    results, bases = [], []
    for block in item.flow.graph.blocks:
        if block.kind != "return" or not path.incoming[block.id]:
            continue
        calls = [node for node in descendants(block.expression) if isinstance(node, ast.FunctionCall)
                 and isinstance(node.callee, ast.Identifier) and node.callee.name == name]
        if not calls:
            bases.append(block.id)
            continue
        results.append({"site": block.id, "self_calls": len(calls), "expression": context.text(block.expression.span),
                        "root_operator": block.expression.operator if isinstance(block.expression, ast.BinaryExpression) else None})
    graph = item.flow.graph
    guards = [{"span": graph.blocks[edge.source].expression.span.to_dict(),
               "condition": context.text(graph.blocks[edge.source].expression.span),
               "outcome": edge.kind == "true"}
              for edge in graph.edges if results and edge in path.edges and edge.target in bases
              and edge.kind in {"true", "false"} and graph.blocks[edge.source].expression is not None]
    return {"recursive_returns": results, "other_return_sites": bases if results else [], "base_guards": guards}


def augment(context, program, previous, entry, examples, enabled):
    paths, locations = {}, {}
    if program.status == "AVAILABLE":
        for item in program.functions:
            path = analyze_paths(context, item, program.bindings, program.deadline)
            paths[item.function.name] = path
            locations[item.function.name] = {"complete": path.complete, "transfers": path.transfers,
                                             "unresolved_conditions": sorted(path.unresolved),
                                             "loop_edges": [{"source": edge.source, "target": edge.target, "kind": edge.kind}
                                                            for edge in item.flow.graph.edges if edge in path.edges and (
                                                                edge.kind in {"back", "break", "continue"}
                                                                or item.flow.graph.blocks[edge.source].kind == "loop_header")],
                                             "returns": return_paths(item, path, program.bindings, program.deadline),
                                             **recurrence_structure(context, item, path)}
    links, links_complete = contracts(program, paths, program.deadline) if paths else ({}, False)
    helpers = scalar_helpers(program, links, program.deadline) if "helpers" in enabled and links else {}
    for name, witness in helpers.items():
        links[name]["scalar_helper"] = witness
    withheld, retained, extra = [], [], []
    for proposal in previous:
        if ("precision" in enabled and proposal.category == "RETURN_DEPENDENCY_MISMATCH"
                and not examples and not precise_return(proposal, locations)):
            withheld.append({"category": proposal.category, "reason": "An unused computed value does not establish that this return is stale.",
                             "span": proposal.edits[0].span.to_dict()})
        else:
            retained.append(proposal)
    for item in program.functions:
        name = item.function.name
        if entry is not None and name != entry:
            continue
        path = paths.get(name)
        if not path or not path.complete or monotonic() >= program.deadline:
            continue
        extra.extend(islice(recursive_candidates(context, item, program.bindings, path, examples, enabled, helpers), MAX_NEW-len(extra)))
        if "precision" in enabled:
            extra.extend(islice(branch_returns(context, item, program.bindings, path, examples), MAX_NEW-len(extra)))
    status = program.status
    if status == "AVAILABLE" and (not links_complete or any(not path.complete for path in paths.values())
                                  or any(not state["dependencies_complete"] for details in locations.values()
                                         for row in details["returns"] for state in row["paths"])
                                  or monotonic() >= program.deadline):
        status = "ANALYSIS_LIMITED"
    return (*extra, *retained), {"status": status, "paths": locations, "interprocedural": links, "withheld": withheld}
