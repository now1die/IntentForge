"""Experimental one-site repairs over local, bounded array computations."""
from compiler import ast_nodes as ast
from analysis_evidence.semantic_state import binding, scalar
from .intention_candidates import Edit, point
from .intention_phase10_flow import walk
from .intention_phase105 import Trial

EMPTY = "EMPTY_ENTRY_RESULT"
AGGREGATE = "AGGREGATE_RESULT_PROJECTION"
CATEGORIES = frozenset({EMPTY, AGGREGATE})


def aggregate_trials(item, index, arrays):
    statements = item.function.body.statements
    tail = statements[-1]
    if not isinstance(tail, ast.ReturnStatement) or not isinstance(tail.value, ast.Identifier):
        return
    counter = binding(index, tail.value)
    for loop in statements:
        if not isinstance(loop, (ast.WhileStatement, ast.ForStatement)):
            continue
        body = tuple(walk(loop.body))
        if not any(isinstance(node, ast.UpdateExpression) and binding(index, node.operand) == counter for node in body):
            continue
        written = {binding(index, node.target.array) for node in body if isinstance(node, ast.Assignment)
                   and isinstance(node.target, ast.ArrayAccess)}
        for key in sorted(written & arrays.keys()):
            name = index.symbols[key].name
            if not any(isinstance(stmt, ast.ArrayDeclaration) and index.declaration(stmt) == key for stmt in statements):
                continue
            for position in sorted({0, arrays[key] - 1}):
                yield Trial(AGGREGATE, (Edit(tail.value.span, f"{name}[{position}]"),),
                            "This traversal updates a count and an array. The supplied outputs support reading an endpoint of the resulting array.")


def entry_trials(item, index, arrays, spec):
    from .intention_phase12 import loop_prefixes
    if not spec.examples or item.function.return_type != "int":
        return
    statements = item.function.body.statements
    for loop, key, length, position in loop_prefixes(item, index, arrays):
        # Require an earlier direct, unguarded seed read from the scanned array.
        seeds = [stmt for stmt in statements if isinstance(stmt, ast.VariableDeclaration)
                 and stmt.span.end.offset <= loop.syntax.span.start.offset
                 and isinstance(stmt.initializer, ast.ArrayAccess)
                 and binding(index, stmt.initializer.array) == key and scalar(stmt.initializer.index) == 0]
        if not seeds or not all(0 <= row.args[position] <= arrays[key] for row in spec.examples):
            continue
        empty = {row.expected_return for row in spec.examples if row.args[position] == 0}
        if len(empty) != 1 or not any(row.args[position] > 0 for row in spec.examples):
            continue
        result = next(iter(empty))
        if type(result) is int:
            name = index.symbols[length].name
            yield Trial(EMPTY, (Edit(point(statements[0].span.start), f"if ({name} == 0) {{ return {result}; }} "),),
                        "The prefix scan uses a fixed array, but its seed reads the first cell even when the supplied length is zero.")
