"""Evidence-based Mini-C hypotheses for engine version 3."""
from collections import Counter
from itertools import combinations, islice, permutations

from compiler.ast_nodes import (
    ArrayAccess, Assignment, BinaryExpression, Block, ForStatement, FunctionCall, Identifier,
    IfStatement, Literal, ReturnStatement, UpdateExpression, VariableDeclaration,
)

from .intention_candidates import Edit, Evidence, Proposal, combine
from .intention_context import ast_children, enclosing, overlapping
from .intention_recovery import (_call_identity, _operator_span, _pure_number_expression,
                                 analogous_operators, call_hypotheses, index_hypotheses)
from .intention_requirements import expression_key


STRONG = frozenset({"STATIC_BOUND", "TYPED_PERMUTATION", "DUPLICATE_GUARD"})


def binding(context, node):
    return context.visible_at(node.span.start.offset).get(node.name) if isinstance(node, Identifier) else None


def _walk(node):
    pending = [node]
    while pending:
        item = pending.pop()
        yield item
        pending.extend(child for _, child in ast_children(item))


def loop_bounds(context):
    for record in context.nodes:
        loop = record.node
        if not isinstance(loop, ForStatement) or not isinstance(loop.body, Block):
            continue
        init, guard, update = loop.initializer, loop.condition, loop.update
        if not (isinstance(init, VariableDeclaration) and init.type_name == "int" and isinstance(init.initializer, Literal)
                and init.initializer.value == 0 and isinstance(guard, BinaryExpression) and guard.operator in {"<", "<="}
                and isinstance(guard.right, Literal) and guard.right.literal_type == "int"
                and isinstance(update, UpdateExpression) and update.operator == "++"):
            continue
        counter = binding(context, guard.left)
        if not counter or counter.declaration_span != init.span or binding(context, update.operand) is not counter:
            continue
        if any((isinstance(node, Assignment) and binding(context, node.target) is counter) or
               (isinstance(node, UpdateExpression) and binding(context, node.operand) is counter)
               for node in _walk(loop.body)):
            continue
        # An unconditional first statement rules out early guards and exits.
        for stmt in loop.body.statements[:1]:
            operands = [stmt.initializer] if isinstance(stmt, VariableDeclaration) else []
            expr = getattr(stmt, "expression", None)
            if isinstance(expr, Assignment):
                operands = [expr.target, expr.value]
            for access in operands:
                if not isinstance(access, ArrayAccess):
                    continue
                array = binding(context, access.array)
                if not array or array.array_size is None or array.array_size <= 0:
                    continue
                maximum = guard.right.value - (guard.operator == "<")
                evidence = (
                    Evidence("STATIC_BOUND", f"The loop starts at zero, increments by one and permits index {maximum}.", guard.span),
                    Evidence("SYMBOL", f"The accessed array has {array.array_size} elements.", array.declaration_span),
                    Evidence("OBSERVED_AST", "The first loop statement directly accesses this array.", access.span),
                )
                if maximum == array.array_size and guard.operator == "<=" and binding(context, access.index) is counter:
                    span = _operator_span(context, guard)
                    if span:
                        yield Proposal((Edit(span, "<"),), "COMPARISON_OPERATOR", evidence,
                                       "The bound may be intended to exclude the array length.", "BinaryExpression", "condition", True)
                index = access.index
                if (maximum == array.array_size - 1 and isinstance(index, BinaryExpression)
                        and index.operator in {"+", "-"} and isinstance(index.right, Literal)
                        and index.right.value == 1 and binding(context, index.left) is counter):
                    yield Proposal((Edit(index.span, counter.name),), "ARRAY_INDEX", evidence,
                                   "The loop counter itself stays in range. The offset may be unintended.",
                                   "ArrayAccess", "index", True)


def typed_permutations(context):
    types = context.semantic.expression_types
    for record in context.nodes:
        call = record.node
        if not isinstance(call, FunctionCall) or not 2 <= len(call.arguments) <= 4:
            continue
        # Reordering calls, assignments, or other potentially effectful expressions
        # could change when side effects happen.
        if not all(isinstance(arg, (Identifier, Literal)) for arg in call.arguments):
            continue
        signature = _call_identity(context, call)
        if not signature or len(signature.type.parameter_types) != len(call.arguments):
            continue
        expected = signature.type.parameter_types
        actual = tuple(types.get(id(arg)) for arg in call.arguments)
        if actual == expected or None in actual or any(t.is_error for t in actual):
            continue
        orders = [order for order in permutations(range(len(actual))) if tuple(actual[i] for i in order) == expected]
        if len(orders) != 1:
            continue
        order = orders[0]
        edits = tuple(Edit(arg.span, context.text(call.arguments[order[i]].span))
                      for i, arg in enumerate(call.arguments) if order[i] != i)
        yield Proposal(edits, "FUNCTION_ARGUMENT",
                       (Evidence("TYPED_PERMUTATION", "Exactly one order matches all declared parameter types.", call.span),
                        Evidence("FUNCTION_SIGNATURE", signature.type.display(), signature.declaration_span)),
                       "The existing argument values may have been passed in the wrong order.",
                       "FunctionCall", "arguments", True)


def consistent_returns(context):
    for record in context.nodes:
        if not isinstance(record.node, Block):
            continue
        statements = record.node.statements
        if not statements or not isinstance(statements[-1], ReturnStatement):
            continue
        tail = statements[-1].value
        if not isinstance(tail, Identifier):
            continue
        selected = binding(context, tail)
        types = context.semantic.expression_types
        for declaration in statements[:-1]:
            if not isinstance(declaration, VariableDeclaration) or not isinstance(declaration.initializer, BinaryExpression):
                continue
            expected = context.visible_at(tail.span.start.offset).get(declaration.name)
            if (not expected or expected is selected or expected.declaration_span != declaration.span
                    or not selected or expected.type != selected.type or not _pure_number_expression(declaration.initializer)):
                continue
            if not any(binding(context, node) is selected for node in _walk(declaration.initializer)):
                continue
            peers = [row.value for stmt in statements[:-1] if isinstance(stmt, IfStatement) for row in _walk(stmt)
                     if isinstance(row, ReturnStatement) and binding(context, row.value) is expected]
            if not peers or not types.get(id(tail)):
                continue
            yield Proposal((Edit(tail.span, expected.name),), "RETURN_EXPRESSION",
                           (Evidence("OBSERVED_AST", "The declaration computes a value from the returned binding.", declaration.span),
                            Evidence("ANALOGOUS_RETURN", "Another return in the same block chooses the computed value.", peers[0].span)),
                           "The final return may also be intended to choose the computed value.",
                           "ReturnStatement", "return", True)


def duplicate_guards(context):
    for record in context.nodes:
        branch = record.node
        if not isinstance(branch, IfStatement) or not isinstance(branch.else_branch, IfStatement):
            continue
        alternate = branch.else_branch.condition
        if (any(not isinstance(node, (Identifier, Literal, BinaryExpression)) for node in _walk(branch.condition))
                or expression_key(branch.condition) != expression_key(alternate)):
            continue
        original_bindings = [binding(context, node) for node in _walk(branch.condition) if isinstance(node, Identifier)]
        repeated_bindings = [binding(context, node) for node in _walk(alternate) if isinstance(node, Identifier)]
        if original_bindings and all(a is not None and a is b for a, b in zip(original_bindings, repeated_bindings, strict=True)):
            return (Evidence("DUPLICATE_GUARD", "The else-if repeats the same side-effect-free guard and bindings.", alternate.span),
                    Evidence("OBSERVED_AST", "This earlier guard must already have evaluated false.", branch.condition.span))
    return ()


def hypotheses(context, *, allow_logic):
    if context.semantic is None:
        return
    yield from typed_permutations(context)
    if not allow_logic or not context.compiler_valid:
        return
    strong = list(islice(loop_bounds(context), 5))
    for left, right in combinations(strong, 2):
        a, b = left.edits[0].span, right.edits[0].span
        if not overlapping(a, b) and a.start != b.start:
            yield combine(left, right, "Two separate array accesses may need corrections.")
            break
    yield from strong
    yield from consistent_returns(context)
    yield from index_hypotheses(context)
    yield from call_hypotheses(context)
    # Require matching right operands rather than congruent types alone.
    for proposal in analogous_operators(context):
        spans = [fact.span for fact in proposal.evidence if fact.span]
        peers = [record.node for record in context.nodes if isinstance(record.node, BinaryExpression) and record.node.span in spans]
        shapes = Counter(str(expression_key(expr.right)) for expr in peers)
        if len(peers) >= 3 and len(shapes) == 1:
            yield proposal


def generalized_features(context, proposal):
    site = proposal.edits[0].span.start.offset
    containing = [row for row in context.nodes if enclosing(row.node.span, site)]
    block = next((row.node for row in reversed(containing) if isinstance(row.node, Block)), None)
    edit = proposal.edits[0].replacement.strip().strip(",").strip()
    chosen = context.visible_at(site).get(edit)
    prior = [stmt for stmt in block.statements if stmt.span.end.offset <= site] if block else []
    inner = sum(isinstance(row.node, (ForStatement, IfStatement)) for row in containing)
    direct_uses = 0
    direct_writes = 0
    if chosen:
        for stmt in prior:
            if isinstance(stmt, (VariableDeclaration, ReturnStatement)) or getattr(stmt, "expression", None) is not None:
                direct_uses += sum(binding(context, node) is chosen for node in _walk(stmt))
                expr = getattr(stmt, "expression", None)
                direct_writes += (isinstance(expr, Assignment) and binding(context, expr.target) is chosen
                                  or isinstance(expr, UpdateExpression) and binding(context, expr.operand) is chosen)
    return {
        "block_direct_uses": min(direct_uses, 6), "block_direct_writes": min(direct_writes, 4),
        "control_depth": min(inner, 6), "block_has_prior_statements": int(bool(prior)),
        "replacement_is_bound": int(chosen is not None), "strong_evidence": int(evidence_strength(proposal)),
        "peer_evidence": min(sum(fact.kind.startswith("ANALOGOUS") for fact in proposal.evidence), 5),
    }


def evidence_strength(proposal):
    return any(fact.kind in STRONG for fact in proposal.evidence)
