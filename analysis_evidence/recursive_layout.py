"""Recognize a guarded base and self-call return through the existing CFG."""
from time import monotonic

from compiler import ast_nodes as ast

from .expression_normalization import Comparison, INT_MIN, INT_MAX, NEGATE
from .interprocedural import descendants


def guarded_layout(item, path, bindings, comparison, *, local_definitions=False, deadline=None):
    flow = item.flow
    live = [block for block in flow.graph.blocks if path.incoming[block.id]]
    guards = [block for block in live if block.kind == "branch"]
    returns = [block for block in live if block.kind == "return"]
    if len(guards) != 1 or len(returns) != 2:
        return None
    guard, = guards
    if guard.id in path.unresolved:
        return None
    reads = set().union(*(flow.effects[block.id].reads for block in live))
    transparent = set()
    for block in live:
        if block.kind in {"entry", "exit", "branch", "return"}:
            continue
        statement = block.syntax
        if block.kind != "statement" or not isinstance(statement, ast.VariableDeclaration):
            return None
        binding = bindings.declaration(statement)
        if not binding or binding in bindings.globals or (not local_definitions and binding in reads):
            return None
        initializer = statement.initializer
        literal = isinstance(initializer, ast.Literal) and (
            type(initializer.value) is bool or type(initializer.value) is int and INT_MIN <= initializer.value <= INT_MAX)
        if initializer is None or (not local_definitions and not literal):
            return None
        transparent.add(block.id)

    outgoing = flow.graph.outgoing()

    def destination(site):
        for _ in range(len(transparent) + 1):
            if site not in transparent:
                return site
            edges = [edge for edge in outgoing[site] if edge in path.edges]
            if len(edges) != 1:
                return None
            site = edges[0].target
        return None

    branch_targets = {edge.kind: destination(edge.target) for edge in outgoing[guard.id] if edge in path.edges}
    if set(branch_targets) != {"true", "false"} or set(branch_targets.values()) != {row.id for row in returns}:
        return None

    def has_self_call(expression):
        return any(isinstance(node, ast.FunctionCall) and isinstance(node.callee, ast.Identifier)
                   and node.callee.name == item.function.name for node in descendants(expression))

    recursive = set()
    for block in returns:
        if has_self_call(block.expression):
            recursive.add(block.id)
        if local_definitions:
            if monotonic() >= deadline:
                return None
            definitions, complete = flow.return_slice(block.id, deadline)
            if not complete:
                return None
            if any(row.site in transparent and has_self_call(flow.graph.blocks[row.site].expression)
                   for row in definitions):
                recursive.add(block.id)
    base = [row for row in returns if row.id not in recursive]
    if len(base) != 1:
        return None
    base, = base
    recurrence = next(block for block in returns if block.id != base.id)
    if branch_targets["false"] == base.id:
        comparison = Comparison(comparison.left, NEGATE[comparison.operator], comparison.right)
    return guard.syntax, base.syntax, recurrence.syntax, comparison
