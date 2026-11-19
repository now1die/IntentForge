"""Scoped static recovery of first-statement array accesses in counted loops."""
from compiler.ast_nodes import (
    ArrayAccess, Assignment, BinaryExpression, Block, BreakStatement, ForStatement, Identifier, Literal, ReturnStatement,
    UnaryExpression, UpdateExpression, VariableDeclaration,
)

from itertools import combinations, islice

from .intention_candidates import Edit, Evidence, Proposal, combine
from .intention_context import overlapping
from .intention_generalization import _walk, binding
from .intention_recovery import _operator_span


def _integer(node):
    if isinstance(node, Literal) and node.literal_type == "int":
        return node.value
    if isinstance(node, UnaryExpression) and node.operator == "-" and isinstance(node.operand, Literal):
        value = _integer(node.operand)
        return -value if value is not None else None
    return None


def _first_accesses(body):
    if not body.statements:
        return ()
    stmt = body.statements[0]
    if isinstance(stmt, VariableDeclaration):
        return (stmt.initializer,)
    expr = getattr(stmt, "expression", None)
    if isinstance(expr, Assignment):
        return expr.target, expr.value
    return ()


def _guard_edit(context, guard, initial, final, step, size, index_delta):
    first_index, last_index = initial + index_delta, final + index_delta
    if not 0 <= first_index < size:
        return None
    # Tighten by exactly one iteration and only when the bound is inclusive.
    replacement = {"<=": "<", ">=": ">"}.get(guard.operator)
    span = _operator_span(context, guard)
    if replacement and span and last_index == (size if step == 1 else -1):
        return Edit(span, replacement)
    return None


def counted_loop_repairs(context):
    if not context.compiler_valid:
        return
    for record in context.nodes:
        loop = record.node
        if not isinstance(loop, ForStatement) or not isinstance(loop.body, Block):
            continue
        init, guard, update = loop.initializer, loop.condition, loop.update
        if not (isinstance(init, VariableDeclaration) and init.type_name == "int"
                and isinstance(guard, BinaryExpression)
                and isinstance(update, UpdateExpression) and update.operator in {"++", "--"}):
            continue
        start = _integer(init.initializer)
        threshold = _integer(guard.right)
        counter = binding(context, guard.left)
        if (start is None or threshold is None or not counter or counter.declaration_span != init.span
                or binding(context, update.operand) is not counter):
            continue
        step = 1 if update.operator == "++" else -1
        if guard.operator not in ({"<", "<="} if step == 1 else {">", ">="}):
            continue
        end = threshold - step if guard.operator in {"<", ">"} else threshold
        if (end - start) * step < 1 or not all(-1_000_000 <= value <= 1_000_000 for value in (start, end)):
            continue
        if any(isinstance(node, (BreakStatement, ReturnStatement))
               or (isinstance(node, Assignment) and binding(context, node.target) is counter)
               or (isinstance(node, UpdateExpression) and binding(context, node.operand) is counter)
               for node in _walk(loop.body)):
            continue
        for access in _first_accesses(loop.body):
            if not isinstance(access, ArrayAccess):
                continue
            array = binding(context, access.array)
            if not array or not array.array_size:
                continue
            ref, delta = access.index, 0
            if isinstance(ref, BinaryExpression) and ref.operator in {"+", "-"} and _integer(ref.right) == 1:
                delta = 1 if ref.operator == "+" else -1
                ref = ref.left
            if not isinstance(ref, Identifier) or binding(context, ref) is not counter:
                continue
            size = array.array_size
            evidence = (
                Evidence("STATIC_BOUND",
                         f"The counter runs from {start} toward {end} in steps of {step}. The first statement indexes the array with offset {delta}.",
                         guard.span),
                Evidence("SYMBOL", f"The referenced array has {size} elements.", array.declaration_span),
            )
            edit = _guard_edit(context, guard, start, end, step, size, delta)
            if edit:
                yield Proposal((edit,), "COMPARISON_OPERATOR", evidence,
                               "The loop may be intended to stop before the last out-of-range access.",
                               "BinaryExpression", "condition", True)
            if delta and min(start, end) == 0 and max(start, end) == size - 1:
                yield Proposal((Edit(access.index.span, ref.name),), "ARRAY_INDEX", evidence,
                               "The unshifted counter spans the declared array. The offset may be unintended.",
                               "ArrayAccess", "index", True)


def phase35_hypotheses(context):
    local = list(islice(counted_loop_repairs(context), 4))
    for left, right in combinations(local, 2):
        a, b = left.edits[0].span, right.edits[0].span
        if left.evidence[0].span != right.evidence[0].span and a.start != b.start and not overlapping(a, b):
            yield combine(left, right, "Separate counted loops each have an array-boundary alternative.")
            break
    yield from local


def phase35_features(context, proposal):
    """Lexical structural features. Candidate names and intended outcomes stay out."""
    edit = proposal.edits[0]
    start = edit.span.start.offset
    name = edit.replacement.strip(", ")
    visible = context.visible_at(start)
    bound = visible.get(name)
    scope = context.scope_at(start)
    return {
        "phase35_visible_choices": min(sum(sym.type.kind.value == "scalar" for sym in visible.values()), 12),
        "phase35_same_lexical_scope": int(bool(bound and scope and bound.scope_id == scope.id)),
        "phase35_edit_span": min(edit.span.end.offset - start, 30),
    }
