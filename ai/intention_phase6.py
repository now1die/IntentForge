"""Dependency-gated Phase 6 synthesis for bounded Mini-C repairs."""
from collections import defaultdict
from itertools import islice
from time import monotonic

from analysis_evidence.expression_normalization import INT_MAX, INT_MIN, normalized_comparison
from compiler import ast_nodes as ast
from compiler.symbol_table import SymbolKind

from .intention_candidates import Edit, Evidence, Proposal
from .intention_context import ast_children

CATEGORIES = frozenset({"RECURSIVE_ARGUMENT_UPDATE", "BASE_CASE_BOUNDARY", "BASE_CASE_RETURN",
                        "RETURN_DEPENDENCY_MISMATCH"})
MAX_PROPOSALS = 6
MATH = {"+", "-", "*"}


def descendants(node):
    pending = [node]
    while pending:
        current = pending.pop()
        yield current
        pending.extend(child for _, child in ast_children(current))


def guarded_return(node):
    if isinstance(node, ast.Block) and len(node.statements) == 1:
        node = node.statements[0]
    return node if isinstance(node, ast.ReturnStatement) and node.value is not None else None


def recursion_proposals(context, item, bindings, domain):
    function = item.function
    statements = function.body.statements
    if len(statements) != 2 or len(function.parameters) != 1 or function.parameters[0].type_name != "int":
        return
    guard, fallback = statements
    if not isinstance(guard, ast.IfStatement) or guard.else_branch is not None or not isinstance(fallback, ast.ReturnStatement):
        return
    base_case = guarded_return(guard.then_branch)
    parameter = bindings.declaration(function.parameters[0])
    compare = normalized_comparison(guard.condition, context.semantic.expression_types, bindings.identifiers, preferred=parameter)
    if not base_case or not compare or not isinstance(compare.left, ast.Identifier) or not isinstance(compare.right, ast.Literal):
        return
    symbol = bindings.identifiers.get(id(compare.left))
    if not symbol or symbol.id != parameter or compare.operator not in {"<", "<=", ">", ">=", "=="}:
        return
    if not isinstance(base_case.value, (ast.Literal, ast.Identifier)) or fallback.value is None:
        return
    parts = tuple(descendants(fallback.value))
    calls = [node for node in parts if isinstance(node, ast.FunctionCall)]
    if len(calls) != 1 or any(not isinstance(node, (ast.Literal, ast.Identifier, ast.BinaryExpression,
                                                  ast.FunctionCall))
                             or isinstance(node, ast.BinaryExpression) and node.operator not in MATH
                             for node in parts):
        return
    call, = calls
    if not isinstance(call.callee, ast.Identifier) or call.callee.name != function.name or len(call.arguments) != 1:
        return
    arg = call.arguments[0]
    bound = compare.right.value
    supporting = Evidence("RECURSIVE_BASE_GUARD", "The first guard returns before the self-call when its comparison holds.", guard.condition.span)
    uncertainty = Evidence("DOMAIN_UNKNOWN", "The intended input domain and recurrence require a specification or additional tests.", function.span)

    def same_parameter(node):
        binding = bindings.identifiers.get(id(node))
        return binding is not None and binding.id == parameter

    direction = {">": "+", ">=": "+", "<": "-", "<=": "-"}.get(compare.operator)
    if direction and same_parameter(arg):
        yield Proposal((Edit(arg.span, f"{symbol.name} {direction} 1"),), "RECURSIVE_ARGUMENT_UPDATE",
                       (supporting, Evidence("RECURSIVE_UNCHANGED_INPUT", "The recursive path passes its parameter unchanged.", arg.span)),
                       "A unit step toward the guarded boundary may be intended.",
                       "FunctionCall", "arguments", type_match=True, counter_evidence=(uncertainty,))
    if compare.operator != "==" or not domain:
        return
    # A trusted example authorizes only its own domain point.
    if isinstance(arg, ast.BinaryExpression) and same_parameter(arg.left) and isinstance(arg.right, ast.Literal) and arg.right.value == 1:
        away = bound - 1 if arg.operator == "-" else bound + 1 if arg.operator == "+" else None
        if away is not None and INT_MIN <= away <= INT_MAX and any(
                len(example.args) == 1 and type(example.args[0]) is int and example.args[0] == away for example in domain):
            yield Proposal((Edit(guard.condition.span, f"({context.text(guard.condition.span)}) || {symbol.name} == {away}"),),
                           "BASE_CASE_BOUNDARY",
                           (supporting, Evidence("SUPPLIED_DOMAIN_POINT", f"A supplied vector covers adjacent input {away}, where the unit step moves away.", arg.span)),
                           "The guarded return may also apply to this supplied input.",
                           "IfStatement", "condition", type_match=True, counter_evidence=(uncertainty,))
    if isinstance(base_case.value, ast.Literal):
        values = {example.expected_return for example in domain if len(example.args) == 1
                  and type(example.args[0]) is int and example.args[0] == bound
                  and type(example.expected_return) is type(base_case.value.value)}
        if len(values) == 1:
            expected, = values
            if expected != base_case.value.value and (type(expected) is bool or INT_MIN <= expected <= INT_MAX):
                literal = str(expected).lower()
                yield Proposal((Edit(base_case.value.span, literal),), "BASE_CASE_RETURN",
                               (supporting, Evidence("SUPPLIED_BASE_RESULT", "The supplied expectation differs from the singleton base return.", base_case.value.span)),
                               "The supplied expectation applies to this exact base input.",
                               "ReturnStatement", "value", type_match=True, counter_evidence=(uncertainty,))


def computed_chain(flow, site, candidate, old, bindings):
    """Find two pure arithmetic definitions from old to candidate."""
    current = flow.for_binding(site, candidate)
    if len(current) != 1:
        return None
    definitions = []
    visited = set()
    while len(definitions) < 4:
        definition, = current
        block = flow.graph.blocks[definition.site]
        node = block.syntax
        if not isinstance(node, ast.VariableDeclaration) or definition.site in visited:
            return None
        expression = node.initializer
        if not isinstance(expression, ast.BinaryExpression) or expression.operator not in MATH:
            return None
        nodes = tuple(descendants(expression))
        if any(not isinstance(part, (ast.Identifier, ast.BinaryExpression, ast.Literal))
               or isinstance(part, ast.BinaryExpression) and part.operator not in MATH for part in nodes):
            return None
        visited.add(definition.site)
        definitions.append(block)
        dependencies = flow.effects[definition.site].reads
        if len(dependencies) != 1:
            return None
        dependency, = dependencies
        if dependency == old:
            # The older binding must have the same reaching definition as at the return.
            before = flow.for_binding(definition.site, old)
            return definitions if len(definitions) >= 2 and len(before) == 1 and before == flow.for_binding(site, old) else None
        if bindings.symbols[dependency].kind != SymbolKind.VARIABLE:
            return None
        current = flow.for_binding(definition.site, dependency)
        if len(current) != 1:
            return None
    return None


def return_proposals(context, item, bindings, deadline):
    flow = item.flow
    if any(flow.effects[site].calls or flow.effects[site].array_access or flow.effects[site].writes & bindings.globals
           for site in item.reachable):
        return
    grouped = defaultdict(list)
    used = set().union(*(flow.effects[site].reads for site in item.reachable))
    for block in flow.graph.blocks:
        if block.id not in item.reachable or block.kind != "return" or not isinstance(block.expression, ast.Identifier):
            continue
        old = bindings.identifiers.get(id(block.expression))
        if old and old.kind == SymbolKind.VARIABLE and old.id not in bindings.globals:
            grouped[old.id].append(block)
    for old, returns in grouped.items():
        if len(returns) > 2:
            continue
        options = {}
        for site in returns:
            valid = {}
            visible = context.visible_at(site.expression.span.start.offset)
            for binding in islice(visible.values(), 24):
                if monotonic() >= deadline:
                    return
                if (binding.id == old or binding.kind != SymbolKind.VARIABLE
                        or binding.type.display() != item.function.return_type or binding.id in bindings.globals
                        or binding.id in used):
                    continue
                chain = computed_chain(flow, site.id, binding.id, old, bindings)
                if chain:
                    valid[binding.id] = chain
            options[site.id] = valid
        possible = set.intersection(*(set(row) for row in options.values()))
        if len(possible) != 1:
            continue
        chosen, = possible
        first = returns[0]
        chain = options[first.id][chosen]
        name = bindings.symbols[chosen].name
        yield Proposal(tuple(Edit(site.expression.span, name) for site in returns), "RETURN_DEPENDENCY_MISMATCH",
                       (Evidence("REACHING_RETURN_BINDING", "Each affected return reads the earlier binding.", first.expression.span),
                        Evidence("COMPUTED_RETURN_DEPENDENCY", "A unique visible result is reached through at least two arithmetic definitions.", chain[0].syntax.span)),
                       "The final computed value may be intended at each marked return.",
                       "ReturnStatement", "value", type_match=True,
                       counter_evidence=(Evidence("INTENTIONAL_INTERMEDIATE", "The function may intentionally expose an intermediate value.", first.syntax.span),))


def proposals(context, program, entry, examples):
    if program.status != "AVAILABLE":
        return ()
    result = []
    for item in program.functions:
        if monotonic() >= program.deadline:
            break
        name = item.function.name
        if entry is not None and name != entry:
            continue
        result.extend(islice(recursion_proposals(context, item, program.bindings, examples), MAX_PROPOSALS-len(result)))
        result.extend(islice(return_proposals(context, item, program.bindings, program.deadline), MAX_PROPOSALS-len(result)))
        if len(result) >= MAX_PROPOSALS:
            break
    return tuple(result)
