"""Bounded call-site dependencies and conservative transitive global effects."""
from dataclasses import dataclass, field
from time import monotonic

from ai.intention_context import ast_children
from compiler import ast_nodes as ast

from .dataflow import effects
from .expression_normalization import INT_MAX

MAX_CALL_SITES = 72
MAX_PROPAGATION = 5


def descendants(node):
    work = [node] if node is not None else []
    while work:
        current = work.pop()
        yield current
        work.extend(child for _, child in reversed(tuple(ast_children(current))))


def atom(node, bindings):
    binding = bindings.identifiers.get(id(node))
    if binding:
        return (binding.id, binding.name, 0)
    if (isinstance(node, ast.BinaryExpression) and node.operator in {"+", "-"}
            and isinstance(node.left, ast.Identifier) and isinstance(node.right, ast.Literal)
            and type(node.right.value) is int and 0 <= node.right.value <= INT_MAX):
        binding = bindings.identifiers.get(id(node.left))
        if binding and binding.type.display() == "int":
            return (binding.id, binding.name, node.right.value * (1 if node.operator == "+" else -1))
    return None


@dataclass(slots=True)
class Call:
    syntax: ast.FunctionCall
    name: str | None
    site: int
    feeds_return: bool


@dataclass(slots=True)
class FunctionCalls:
    calls: list[Call] = field(default_factory=list)
    local_reads: set[str] = field(default_factory=set)
    local_writes: set[str] = field(default_factory=set)
    return_inputs: set[int] = field(default_factory=set)
    forwarding: tuple[str, tuple[int | None, ...]] | None = None
    complete: bool = True


def inspect(item, reachable, bindings, deadline, budget):
    function, flow = item.function, item.flow
    summary = FunctionCalls(complete=flow.complete)
    return_sites = {block.id for block in flow.graph.blocks if block.kind == "return" and block.id in reachable}
    value_sites = set(return_sites)
    for site in sorted(return_sites):
        definitions, complete = flow.return_slice(site, deadline)
        summary.complete &= complete
        value_sites.update(row.site for row in definitions)
    writes = set()
    for site in sorted(reachable):
        if monotonic() >= deadline:
            summary.complete = False
            break
        block = flow.graph.blocks[site]
        effect = effects(block.expression, bindings, conservative_calls=False)
        writes.update(effect.writes)
        summary.local_reads.update(effect.reads & bindings.globals)
        summary.local_writes.update(effect.writes & bindings.globals)
        for node in descendants(block.expression):
            if isinstance(node, ast.FunctionCall):
                if len(summary.calls) >= budget:
                    summary.complete = False
                    break
                name = node.callee.name if isinstance(node.callee, ast.Identifier) else None
                summary.calls.append(Call(node, name, site, site in value_sites))
    # Refine direct return expressions in straight-line bodies only.
    parameters = {bindings.declaration(parameter): index for index, parameter in enumerate(function.parameters)}
    summary.return_inputs = set(range(len(function.parameters)))
    statements = function.body.statements
    if (len(return_sites) == 1 and statements
            and all(isinstance(statement, (ast.VariableDeclaration, ast.ExpressionStatement)) for statement in statements[:-1])):
        statement = statements[-1]
        value = statement.value if isinstance(statement, ast.ReturnStatement) else None
        if isinstance(value, ast.Literal):
            summary.return_inputs.clear()
        elif isinstance(value, ast.Identifier):
            bound = bindings.identifiers.get(id(value))
            if bound and bound.id in parameters and bound.id not in writes:
                summary.return_inputs = {parameters[bound.id]}
        elif isinstance(value, ast.FunctionCall) and isinstance(value.callee, ast.Identifier):
            mapped = []
            for argument in value.arguments:
                bound = bindings.identifiers.get(id(argument))
                if bound and bound.id in parameters and bound.id not in writes:
                    mapped.append(parameters[bound.id])
                elif isinstance(argument, ast.Literal) and type(argument.value) in {int, bool}:
                    mapped.append(None)
                else:
                    break
            else:
                summary.forwarding = (value.callee.name, tuple(mapped))
    return summary


def contracts(program, paths, deadline):
    bindings = program.bindings
    if bindings is None:
        return {}, True
    rows, remaining = {}, MAX_CALL_SITES
    functions = {item.function.name: item.function for item in program.functions}
    for item in program.functions:
        name = item.function.name
        path = paths.get(name)
        reachable = {site for site, states in enumerate(path.incoming) if states} if path and path.complete else item.reachable
        rows[name] = inspect(item, reachable, bindings, deadline, remaining)
        remaining -= len(rows[name].calls)
    unknown = {name for name, row in rows.items()
               if not row.complete or any(call.name not in rows for call in row.calls)}
    effects_by_name = {name: (row.local_reads.copy(), row.local_writes.copy()) for name, row in rows.items()}
    for _ in range(MAX_PROPAGATION):
        changed = False
        for name, row in rows.items():
            reads, writes = effects_by_name[name]
            for call in row.calls:
                if call.name not in rows or call.name in unknown:
                    changed |= name not in unknown
                    unknown.add(name)
                    continue
                remote_reads, remote_writes = effects_by_name[call.name]
                before = len(reads) + len(writes)
                reads.update(remote_reads)
                writes.update(remote_writes)
                changed |= before != len(reads) + len(writes)
            if row.forwarding:
                target, mapping = row.forwarding
                if target in rows and target not in unknown:
                    refined = {mapping[i] for i in rows[target].return_inputs
                               if i < len(mapping) and mapping[i] is not None}
                    changed |= refined != row.return_inputs
                    row.return_inputs = refined
        if not changed:
            break
    else:
        unknown.update(rows)
    result = {}
    for name, row in rows.items():
        calls = []
        for call in row.calls:
            callee = functions.get(call.name)
            effect = rows.get(call.name)
            mapped = []
            for i, argument in enumerate(call.syntax.arguments):
                relation = atom(argument, bindings)
                mapped.append({
                    "position": i, "parameter": callee.parameters[i].name if callee and i < len(callee.parameters) else None,
                    "dependencies": sorted(effects(argument, bindings).reads),
                    "affine": {"binding": relation[0], "name": relation[1], "offset": relation[2]} if relation else None,
                })
            calls.append({"target": call.name, "span": call.syntax.span.to_dict(), "arguments": mapped,
                          "feeds_return": call.feeds_return, "self_recursive": call.name == name,
                          "callee_result_inputs": sorted(effect.return_inputs) if effect and call.name not in unknown else None})
        reads, writes = effects_by_name[name]
        result[name] = {"call_sites": calls, "return_parameter_inputs": sorted(
                            range(len(functions[name].parameters)) if name in unknown else row.return_inputs),
                        "possible_global_reads": sorted(bindings.globals if name in unknown else reads),
                        "possible_global_writes": sorted(bindings.globals if name in unknown else writes),
                        "effects_unknown": name in unknown, "complete": name not in unknown}
    return result, not unknown


def scalar_helpers(program, summaries, deadline, *, local_definitions=False):
    """Describe small, acyclic scalar helpers over parameters and literals.

    Arithmetic can still fault under checked Mini-C semantics. This witness
    certifies data dependence and the absence of mutable effects, not totality.
    """
    helpers = {}
    bindings = program.bindings
    for _ in range(3):
        changed = False
        for item in program.functions:
            function = item.function
            if monotonic() >= deadline:
                return helpers
            row = summaries.get(function.name)
            body = function.body.statements
            if (function.name in helpers or not row or not row["complete"] or row["possible_global_reads"]
                    or row["possible_global_writes"]):
                continue
            if local_definitions:
                witness = scalar_cfg_helper(item, bindings, helpers)
                if witness is not None:
                    helpers[function.name] = witness
                    changed = True
                continue
            if len(body) != 1 or not isinstance(body[0], ast.ReturnStatement) or body[0].value is None:
                continue
            positions = {bindings.declaration(parameter): n for n, parameter in enumerate(function.parameters)}
            expressions = [body[0].value]
            inputs, depth, nodes = set(), 0, 0
            while expressions and nodes < 48:
                node = expressions.pop()
                nodes += 1
                if isinstance(node, ast.Literal) and type(node.value) in {int, bool}:
                    continue
                if isinstance(node, ast.Identifier):
                    binding = bindings.identifiers.get(id(node))
                    if binding and binding.id in positions:
                        inputs.add(positions[binding.id])
                        continue
                elif isinstance(node, ast.BinaryExpression) and node.operator in {"+", "-", "*"}:
                    expressions.extend((node.left, node.right))
                    continue
                elif isinstance(node, ast.FunctionCall) and isinstance(node.callee, ast.Identifier):
                    callee = helpers.get(node.callee.name)
                    if callee and callee["depth"] < 2:
                        depth = max(depth, callee["depth"] + 1)
                        # Every actual is evaluated, so conservatively include
                        # their dependencies even if the callee ignores one.
                        expressions.extend(node.arguments)
                        continue
                break
            else:
                if not expressions:
                    value = body[0].value
                    parameter = bindings.identifiers.get(id(value)) if isinstance(value, ast.Identifier) else None
                    helpers[function.name] = {"parameter_inputs": sorted(inputs), "depth": depth,
                                              "identity_parameter": positions[parameter.id] if parameter else None}
                    changed = True
        if not changed:
            break
    return helpers



def local_initializer(flow, site, binding, bindings):
    """Return the unique scalar declaration that reaches this lexical read."""
    definitions = flow.for_binding(site, binding)
    if len(definitions) != 1:
        return None
    definition, = definitions
    node = flow.graph.blocks[definition.site].syntax
    if isinstance(node, ast.VariableDeclaration) and bindings.declaration(node) == binding and node.initializer is not None:
        return definition.site, node.initializer
    return None


def scalar_cfg_helper(item, bindings, helpers):
    flow = item.flow
    blocks = [block for block in flow.graph.blocks if block.id in item.reachable]
    returns = [block for block in blocks if block.kind == "return"]
    if not returns or len(blocks) > 24 or any(
        edge.target == flow.graph.exit and edge.kind != "return" and edge.source in item.reachable
        for edge in flow.graph.edges
    ):
        return None
    parameters = {bindings.declaration(parameter): i for i, parameter in enumerate(item.function.parameters)}
    expressions = []
    for block in blocks:
        if block.kind in {"entry", "exit"}:
            continue
        if block.kind in {"return", "branch"} and block.expression is not None:
            expressions.append((block.id, block.expression))
        elif block.kind == "statement" and isinstance(block.syntax, ast.VariableDeclaration) and block.syntax.initializer is not None:
            expressions.append((block.id, block.syntax.initializer))
        else:
            return None
    inputs, depth, visited = set(), 0, 0
    while expressions:
        site, node = expressions.pop()
        visited += 1
        if visited > 72:
            return None
        if isinstance(node, ast.Literal) and type(node.value) in {int, bool}:
            continue
        if isinstance(node, ast.Identifier):
            binding = bindings.identifiers.get(id(node))
            if binding and binding.id in parameters:
                inputs.add(parameters[binding.id])
                continue
            if binding and local_initializer(flow, site, binding.id, bindings):
                # The declaration's initializer is checked in its own CFG block.
                continue
        elif isinstance(node, ast.UnaryExpression) and node.operator in {"!", "-", "+"}:
            expressions.append((site, node.operand))
            continue
        elif isinstance(node, ast.BinaryExpression) and node.operator in {
            "+", "-", "*", "/", "%", "<", ">", "<=", ">=", "==", "!=",
        }:
            expressions.extend(((site, node.left), (site, node.right)))
            continue
        elif isinstance(node, ast.FunctionCall) and isinstance(node.callee, ast.Identifier):
            callee = helpers.get(node.callee.name)
            if callee and callee["depth"] < 2:
                depth = max(depth, callee["depth"] + 1)
                expressions.extend((site, argument) for argument in node.arguments)
                continue
        return None

    identity = None
    if len(returns) == 1:
        site, expression = returns[0].id, returns[0].expression
        for _ in range(8):
            if not isinstance(expression, ast.Identifier):
                break
            binding = bindings.identifiers.get(id(expression))
            if not binding:
                break
            if binding.id in parameters:
                identity = parameters[binding.id]
                break
            declaration = local_initializer(flow, site, binding.id, bindings)
            if not declaration:
                break
            site, expression = declaration
    return {"parameter_inputs": sorted(inputs), "depth": depth, "identity_parameter": identity,
            "modeled_returns": len(returns)}
