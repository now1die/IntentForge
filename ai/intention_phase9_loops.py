"""Compiler-backed affine induction and finite scalar transfer summaries."""
from dataclasses import dataclass
from time import monotonic

from compiler import ast_nodes as ast

from .intention_phase8 import ProjectionLimit, Term, UnsupportedProjection, signed, substitution
from .intention_phase85 import MAX_LOOP_POINTS, ScalarProjection

ORDER = {"<": ">", "<=": ">=", ">": "<", ">=": "<="}
MAX_CARRIERS = 2
MAX_BODY_NODES = 10


@dataclass(frozen=True, slots=True)
class Transfer:
    bindings: tuple[str, ...]
    seeds: tuple[Term, ...]
    initial: Term
    bound: Term
    step_term: Term
    step_sign: int
    inclusive: Term
    direction: int
    before: tuple[Term, ...]
    body: tuple[Term, ...]
    outputs: tuple[Term, ...]
    after: tuple[Term, ...]
    result: Term
    source: dict


def bind_declaration(projector, node, values):
    binding = projector.bindings.declaration(node)
    if binding is None or node.type_name != "int" or node.initializer is None:
        raise UnsupportedProjection
    value = projector.expression(node.initializer, values, 0)
    values[binding] = value
    return value


def successors(graph, outgoing, site):
    edges = outgoing[site]
    if len(edges) != 1 or edges[0].kind != "next":
        raise UnsupportedProjection
    return graph.blocks[edges[0].target]


def body_region(graph, outgoing, header):
    edges = {edge.kind: edge.target for edge in outgoing[header.id]}
    if set(edges) != {"true", "false"}:
        raise UnsupportedProjection
    latch = [edge.source for edge in graph.edges if edge.kind == "back" and edge.target == header.id]
    if len(latch) != 1:
        raise UnsupportedProjection
    pending, seen = [edges["true"]], set()
    while pending:
        site = pending.pop()
        if site == latch[0] or site in seen:
            continue
        if len(seen) >= MAX_BODY_NODES or graph.blocks[site].kind not in {"statement", "branch"}:
            raise UnsupportedProjection
        seen.add(site)
        pending.extend(edge.target for edge in outgoing[site])
    return sorted(seen), graph.blocks[edges["false"]]


def step_expression(projector, index, update, invariant):
    if isinstance(update, ast.UpdateExpression) and projector.identifier(update.operand) == index:
        return Term("literal", value=1), 1 if update.operator == "++" else -1
    if not isinstance(update, ast.Assignment) or projector.identifier(update.target) != index:
        raise UnsupportedProjection
    if update.operator in {"+=", "-="}:
        return projector.expression(update.value, invariant, 0), 1 if update.operator == "+=" else -1
    rhs = update.value
    if update.operator != "=" or not isinstance(rhs, ast.BinaryExpression) or rhs.operator not in {"+", "-"}:
        raise UnsupportedProjection
    if projector.identifier(rhs.left) == index:
        return projector.expression(rhs.right, invariant, 0), 1 if rhs.operator == "+" else -1
    if rhs.operator == "+" and projector.identifier(rhs.right) == index:
        return projector.expression(rhs.left, invariant, 0), 1
    raise UnsupportedProjection


def body_transfer(projector, node, values, carriers, depth=0):
    if depth > MAX_BODY_NODES:
        raise ProjectionLimit
    if isinstance(node, ast.Block):
        obligations = []
        for statement in node.statements:
            obligations.extend(body_transfer(projector, statement, values, carriers, depth+1))
        return obligations
    if isinstance(node, ast.IfStatement):
        if depth > 3:
            raise UnsupportedProjection
        condition = projector.boolean(node.condition, values)
        yes, no = dict(values), dict(values)
        first = body_transfer(projector, node.then_branch, yes, carriers, depth+1)
        second = body_transfer(projector, node.else_branch, no, carriers, depth+1) if node.else_branch else []
        for binding in carriers:
            if yes[binding] is not no[binding]:
                values[binding] = Term("select", (condition, yes[binding], no[binding]))
        return [Term("select", (condition, Term("sequence", tuple(first)), Term("sequence", tuple(second))))]
    if isinstance(node, ast.VariableDeclaration):
        return [bind_declaration(projector, node, values)]
    expression = node.expression if isinstance(node, ast.ExpressionStatement) else node
    if isinstance(expression, ast.UpdateExpression):
        target = projector.identifier(expression.operand)
        operator = "+" if expression.operator == "++" else "-"
        if target not in carriers:
            raise UnsupportedProjection
        result = Term(operator, (values[target], Term("literal", value=1)))
    elif isinstance(expression, ast.Assignment) and expression.operator in {"=", "+=", "-="}:
        target = projector.identifier(expression.target)
        if target not in carriers:
            raise UnsupportedProjection
        result = projector.expression(expression.value, values, 0)
        if expression.operator != "=":
            result = Term(expression.operator[0], (values[target], result))
    else:
        raise UnsupportedProjection
    values[target] = result
    return [result]


def simple_count(node):
    while isinstance(node, ast.Block) and len(node.statements) == 1:
        node = node.statements[0]
    if isinstance(node, ast.IfStatement):
        if node.else_branch is not None:
            return False
        node = node.then_branch
        while isinstance(node, ast.Block) and len(node.statements) == 1:
            node = node.statements[0]
    expression = node.expression if isinstance(node, ast.ExpressionStatement) else node
    return isinstance(expression, ast.UpdateExpression) or (
        isinstance(expression, ast.Assignment) and expression.operator in {"+=", "-="}
        and isinstance(expression.value, ast.Literal) and type(expression.value.value) is int
    )


def build_loop(projector: ScalarProjection, item, *, variable=True, mixed=True):
    graph = item.flow.graph
    candidates = [block for block in graph.blocks if block.id in item.reachable and block.kind == "loop_header"]
    if len(candidates) != 1 or not isinstance(candidates[0].syntax, ast.ForStatement):
        raise UnsupportedProjection
    header = candidates[0]
    loop = header.syntax
    initial, guard = loop.initializer, loop.condition
    if (not isinstance(initial, ast.VariableDeclaration) or not isinstance(guard, ast.BinaryExpression)
            or guard.operator not in ORDER):
        raise UnsupportedProjection
    index = projector.bindings.declaration(initial)
    outgoing = graph.outgoing()
    region, exit_block = body_region(graph, outgoing, header)
    parameter_values = projector.entry_locals(item)
    entered, origins = dict(parameter_values), {}
    before = []
    block = successors(graph, outgoing, graph.entry)
    while block.id != header.id:
        node = block.syntax
        if block.kind != "statement" or not isinstance(node, ast.VariableDeclaration):
            raise UnsupportedProjection
        before.append(bind_declaration(projector, node, entered))
        origins[projector.bindings.declaration(node)] = node.span
        block = successors(graph, outgoing, block.id)
    written = set().union(*(item.flow.effects[site].writes for site in region))
    carriers = tuple(binding for binding in entered if binding in written and binding != index)
    if not 1 <= len(carriers) <= (MAX_CARRIERS if mixed else 1) or any(
            binding not in origins for binding in carriers):
        raise UnsupportedProjection
    invariant = {binding: term for binding, term in entered.items() if binding not in carriers and binding != index}
    source_operator = guard.operator
    if projector.identifier(guard.left) == index:
        normalized, limit = source_operator, guard.right
    elif projector.identifier(guard.right) == index:
        normalized, limit = ORDER[source_operator], guard.left
    else:
        raise UnsupportedProjection
    direction = 1 if normalized in {"<", "<="} else -1
    bound = projector.expression(limit, invariant, 0)
    step, sign = step_expression(projector, index, loop.update, invariant)
    if not variable and step.operation != "literal":
        raise UnsupportedProjection
    projector.comparison_change(guard)
    # Compare equal endpoints to read strictness from the original operator or its edit.
    equal = Term("literal", value=0)
    inclusive = Term(source_operator, (equal, equal), origin=id(guard))

    arity = len(parameter_values)
    carried = {binding: Term("parameter", value=arity + 1 + position)
               for position, binding in enumerate(carriers)}
    body_env = {**invariant, **carried, index: Term("parameter", value=arity)}
    if not mixed and not simple_count(loop.body):
        raise UnsupportedProjection
    body = tuple(body_transfer(projector, loop.body, body_env, carriers))
    after_env = {**invariant, **carried}
    after = []
    block = exit_block
    while block.kind != "return":
        if block.kind != "statement" or not isinstance(block.syntax, ast.VariableDeclaration):
            raise UnsupportedProjection
        after.append(bind_declaration(projector, block.syntax, after_env))
        block = successors(graph, outgoing, block.id)
    if block.expression is None:
        raise UnsupportedProjection
    result = projector.expression(block.expression, after_env, 0)
    return Transfer(
        carriers, tuple(entered[key] for key in carriers), entered[index], bound, step, sign,
        inclusive, direction, tuple(before), body, tuple(body_env[key] for key in carriers), tuple(after), result,
        {"guard_span": guard.span.to_dict(), "update_span": loop.update.span.to_dict(), "return_span": block.syntax.span.to_dict(),
         "normalized_relation": normalized, "step_expression": projector.context.text(loop.update.span),
         "variable_step": step.operation != "literal", "direction": "ascending" if direction > 0 else "descending",
         "guard_reversed": limit is guard.left, "exit": "GUARD_FALSE", "point_limit": MAX_LOOP_POINTS,
         "carriers": [{"name": projector.bindings.symbols[key].name, "span": origins[key].to_dict()} for key in carriers],
         "body_spans": [graph.blocks[site].syntax.span.to_dict() for site in region],
         "scope": "SUPPLIED_EXAMPLES_ONLY", "checked_arithmetic": True},
    )


def loop_value(loop, args, changes, deadline, on_fault=None):
    evaluate = substitution(args, changes, on_fault=on_fault)
    for obligation in loop.before:
        evaluate(obligation)
    first, bound = evaluate(loop.initial), evaluate(loop.bound)
    state = tuple(evaluate(term) for term in loop.seeds)
    distance = (bound-first)*loop.direction + int(evaluate(loop.inclusive))
    step, count = None, 0
    if distance > 0:
        step = evaluate(loop.step_term)*loop.step_sign
        magnitude = step*loop.direction
        if not 1 <= magnitude <= MAX_LOOP_POINTS:
            raise UnsupportedProjection
        count = (distance + magnitude - 1)//magnitude
        if count > MAX_LOOP_POINTS:
            raise ProjectionLimit
        end = signed(first + count*step)
        for index in range(first, end, step):
            if monotonic() >= deadline:
                raise ProjectionLimit
            point = substitution((*args, index, *state), changes, on_fault=on_fault)
            for term in loop.body:
                point(term)
            state = tuple(point(term) for term in loop.outputs)
    evaluate_exit = substitution((*args, 0, *state), changes, on_fault=on_fault)
    for obligation in loop.after:
        evaluate_exit(obligation)
    return evaluate_exit(loop.result), count, step, state
