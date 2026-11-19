"""Bounded alternatives inferred from observable Mini-C structure."""

from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import replace
from itertools import combinations, islice

from compiler.ast_nodes import (
    ArrayAccess, Assignment, ASTNode, BinaryExpression, Block, FunctionCall, Identifier,
    IfStatement, Literal, ReturnStatement, UnaryExpression, UpdateExpression, VariableDeclaration,
)
from compiler.source_location import SourceSpan

from .intention_candidates import (Edit, Evidence, MAX_CANDIDATES, Proposal, combine, point,
                                   semantic_proposals, symbol_alternatives)
from .intention_context import IntentionContext, ast_children, overlapping


ARITHMETIC = frozenset({"+", "-", "*", "/", "%"})
COMPARISON = frozenset({"<", "<=", ">", ">=", "==", "!="})


def _identifiers(node: ASTNode) -> set[str]:
    work = [node]
    names = set()
    while work:
        current = work.pop()
        if isinstance(current, Identifier):
            names.add(current.name)
        work.extend(child for _, child in ast_children(current))
    return names


def _pure_number_expression(node: ASTNode) -> bool:
    if isinstance(node, (Identifier, Literal)):
        return True
    if isinstance(node, BinaryExpression):
        return node.operator in ARITHMETIC and _pure_number_expression(node.left) and _pure_number_expression(node.right)
    return isinstance(node, UnaryExpression) and node.operator in {"+", "-"} and _pure_number_expression(node.operand)


def return_hypotheses(context: IntentionContext):
    for record in context.nodes:
        node = record.node
        if not isinstance(node, Block):
            continue
        for declaration, returned in zip(node.statements, node.statements[1:]):
            if (not isinstance(declaration, VariableDeclaration)
                    or not isinstance(declaration.initializer, BinaryExpression)
                    or not isinstance(returned, ReturnStatement) or returned.value is None):
                continue
            init = declaration.initializer
            used = _identifiers(init)
            observed = returned.value
            if (len(used) < 2 or declaration.name in used or not _pure_number_expression(init)
                    or not _pure_number_expression(observed)
                    or not _identifiers(observed) or not _identifiers(observed) <= used
                    or (isinstance(observed, BinaryExpression) and init.operator == observed.operator)):
                continue
            visible = context.visible_at(observed.span.start.offset)
            if declaration.name not in visible or visible[declaration.name].declaration_span != declaration.span:
                continue
            yield Proposal(
                (Edit(observed.span, declaration.name),), "RETURN_EXPRESSION",
                (Evidence("DEF_USE", f"{declaration.name} is computed immediately before this return.", declaration.span),
                 Evidence("OBSERVED_AST", "The return uses inputs of that computation and leaves the computed value unused here.", observed.span)),
                "The preceding computation may have been intended as the return value.", type(observed).__name__, "return_value",
            )


def _operator_span(context, expr):
    return next((t.span for t in context.parsed.tokens if expr.left.span.end.offset <= t.offset < expr.right.span.start.offset
                 and t.lexeme == expr.operator), None)


def analogous_operators(context: IntentionContext):
    """Compare contiguous sibling declarations or branches with bound operands."""
    for record in context.nodes:
        if not isinstance(record.node, Block):
            continue
        runs = defaultdict(list)
        for index, statement in enumerate(record.node.statements):
            if isinstance(statement, VariableDeclaration):
                expr = statement.initializer
                role = "initializer"
            elif isinstance(statement, IfStatement):
                expr = statement.condition
                role = "condition"
            else:
                continue
            if not isinstance(expr, BinaryExpression) or not isinstance(expr.left, Identifier):
                continue
            # Identifier and literal values become structural categories, except that
            # sibling guards must share their literal threshold.
            if isinstance(expr.right, Identifier):
                rhs = ("binding",)
            elif isinstance(expr.right, Literal):
                rhs = ("literal", expr.right.literal_type, expr.right.value if role == "condition" else None)
            else:
                continue
            operators = COMPARISON if role == "condition" else ARITHMETIC
            if expr.operator not in operators or not context.semantic:
                continue
            types = context.semantic.expression_types
            left_type = types.get(id(expr.left))
            right_type = types.get(id(expr.right))
            if not left_type or not right_type or left_type.is_error or right_type.is_error:
                continue
            if role == "condition":
                # Compare the same branch kind and target, keeping different
                # actions out of an analogy even when conditions look alike.
                branch = statement.then_branch
                if isinstance(branch, Block):
                    if len(branch.statements) != 1:
                        continue
                    branch = branch.statements[0]
                action = getattr(branch, "expression", None)
                if statement.else_branch is not None:
                    continue
                if isinstance(action, Assignment) and isinstance(action.target, Identifier) and isinstance(action.value, Literal):
                    action_key = ("assignment", action.target.name, action.operator, action.value.value)
                elif isinstance(action, UpdateExpression) and isinstance(action.operand, Identifier):
                    action_key = ("update", action.operand.name, action.operator)
                else:
                    continue
            else:
                action_key = None
            runs[(role, left_type.display(), right_type.display(), rhs, action_key)].append((index, expr))
        for (role, *_), group in runs.items():
            for i, (position, expr) in enumerate(group):
                others = [(j, peer) for j, peer in group if j != position and abs(j - position) <= 5
                          and peer.left.name != expr.left.name]
                supports = Counter(peer.operator for _, peer in others)
                if not supports or supports.get(expr.operator, 0) > 0 or len({peer.left.name for _, peer in others}) < 2:
                    continue
                span = _operator_span(context, expr)
                if not span:
                    continue
                for operator, count in supports.most_common(2):
                    if count >= 2:
                        peers = [peer for _, peer in others if peer.operator == operator]
                        if len({peer.left.name for peer in peers}) < 2:
                            continue
                        yield Proposal(
                            (Edit(span, operator),), "COMPARISON_OPERATOR" if role == "condition" else "ARITHMETIC_OPERATOR",
                            (Evidence("OBSERVED_AST", f"This {role} uses {expr.operator!r}.", expr.span),
                             *(Evidence("ANALOGOUS_EXPRESSION", f"A nearby {role} with comparable operand types uses {operator!r}.", p.span)
                               for p in peers[:3])),
                            "These nearby expressions may be intended to use the same operation.", "BinaryExpression", role,
                        )


def _call_identity(context, call):
    if isinstance(call.callee, Identifier):
        binding = context.visible_at(call.callee.span.start.offset).get(call.callee.name)
        if binding and binding.kind.value == "function":
            return binding


def call_hypotheses(context: IntentionContext):
    grouped = defaultdict(list)
    for record in context.nodes:
        call = record.node
        if isinstance(call, FunctionCall) and len(call.arguments) == 2 and all(isinstance(arg, Identifier) for arg in call.arguments):
            callee = _call_identity(context, call)
            if callee and len(callee.type.parameter_types) == 2 and record.function:
                key = callee.id, record.function.name
                arguments = tuple(context.visible_at(arg.span.start.offset).get(arg.name) for arg in call.arguments)
                if all(arguments) and arguments[0] is not arguments[1]:
                    grouped[key].append((call, callee, arguments))
    for entries in grouped.values():
        for call, callee, arguments in entries:
            observed = tuple(arg.id for arg in arguments)
            peers = [other for other, _, bindings in entries if tuple(b.id for b in bindings) == observed[::-1]]
            same = [other for other, _, bindings in entries if other is not call and tuple(b.id for b in bindings) == observed]
            expected = callee.type.parameter_types
            actual = tuple(arg.type for arg in arguments)
            typed_swap = actual[::-1] == expected and actual != expected
            if not typed_swap and (len(peers) < 2 or same):
                continue
            left, right = call.arguments
            evidence = Evidence("FUNCTION_SIGNATURE", f"The signature is {callee.type.display()}.", callee.declaration_span)
            extra = tuple(Evidence("ANALOGOUS_CALL", "This call passes the same bindings in the opposite order.", item.span) for item in peers[:3])
            yield Proposal(
                (Edit(left.span, right.name), Edit(right.span, left.name)), "FUNCTION_ARGUMENT",
                (evidence, *extra), "These two arguments may have been transposed.", "FunctionCall", "arguments",
                type_match=typed_swap,
            )


def argument_gaps(context):
    if not context.semantic:
        return
    diagnostics = {item.span: item for item in context.semantic.diagnostics if item.code == "SEM-FUNCTION-ARG-COUNT"}
    for record in context.nodes:
        call = record.node
        if not isinstance(call, FunctionCall) or call.span not in diagnostics:
            continue
        signature = _call_identity(context, call)
        if not signature or len(call.arguments) + 1 != len(signature.type.parameter_types):
            continue
        expected = list(signature.type.parameter_types)
        actual = [context.semantic.expression_types.get(id(arg)) for arg in call.arguments]
        for i, argument in enumerate(call.arguments[:4]):
            without_gap = expected[:i] + expected[i + 1:]
            if not all(found and (found == target or (found.display(), target.display()) == ("int", "float"))
                       for found, target in zip(actual, without_gap, strict=True)):
                continue
            at = point(argument.span.start)
            for proposal in symbol_alternatives(context, record, at, expected[i].display(),
                                                "FUNCTION_ARGUMENT", diagnostics[call.span]):
                edit = proposal.edits[0]
                yield replace(proposal, edits=(Edit(at, edit.replacement.strip() + ", "),),
                              evidence=(*proposal.evidence, Evidence(
                                  "FUNCTION_SIGNATURE", f"Existing arguments fit the signature with a gap at slot {i + 1}.",
                                  signature.declaration_span,
                              )))


def index_hypotheses(context: IntentionContext):
    groups = defaultdict(list)
    for record in context.nodes:
        expr = record.node
        if isinstance(expr, ArrayAccess) and isinstance(expr.array, Identifier) and isinstance(expr.index, Literal):
            array = context.visible_at(expr.array.span.start.offset).get(expr.array.name)
            if array and array.array_size is not None and expr.index.literal_type == "int":
                groups[array.id].append((expr, array))
    for entries in groups.values():
        for expr, array in entries:
            index = expr.index.value
            if 0 <= index < array.array_size:
                continue
            peers = Counter(
                other.index.value for other, _ in entries
                if 0 <= other.index.value < array.array_size
            )
            for value, _ in peers.most_common(2):
                peer = next(other for other, _ in entries if other.index.value == value)
                yield Proposal(
                    (Edit(expr.index.span, str(value)),), "ARRAY_INDEX",
                    (Evidence("SYMBOL", f"{array.name} has a declared extent of {array.array_size}.", array.declaration_span),
                     Evidence("OBSERVED_AST", f"The literal index {index} lies outside that extent.", expr.index.span),
                     Evidence("ANALOGOUS_EXPRESSION", f"A use of the same binding accesses index {value}.", peer.span)),
                    "A previously used in-range index is a possible alternative.", "ArrayAccess", "index",
                )


def local_hypotheses(context, *, allow_heuristics):
    if not context.semantic:
        return
    if allow_heuristics:
        if context.compiler_valid:
            yield from return_hypotheses(context)
            yield from analogous_operators(context)
            yield from index_hypotheses(context)
        yield from call_hypotheses(context)
    yield from argument_gaps(context)


def _role_category(proposal):
    if proposal.category == "VARIABLE_REFERENCE":
        category = {"index": "ARRAY_INDEX", "arguments": "FUNCTION_ARGUMENT", "initializer": "DECLARATION_TYPE"}.get(proposal.role)
        if category:
            return replace(proposal, category=category)
    return proposal


def expanded_proposals(context, proposals, *, allow_heuristics):
    """Diverse independent diagnostic pairs, capped before compiler checks."""
    guesses = list(islice(local_hypotheses(context, allow_heuristics=allow_heuristics), 8))
    semantic = [_role_category(proposal) for proposal in islice(semantic_proposals(context), MAX_CANDIDATES)]
    groups = defaultdict(list)
    for proposal in semantic:
        span = proposal.edits[0].span
        groups[(span.start.offset, span.end.offset)].append(proposal)
    # Round robin across diagnostics so one ambiguous use cannot exhaust all slots.
    slots = list(groups.values())
    pairs = 0
    for left_group, right_group in combinations(slots[:4], 2):
        for left in left_group[:2]:
            for right in right_group[:2]:
                a, b = left.edits[0].span, right.edits[0].span
                if a.start == b.start or overlapping(a, b):
                    continue
                yield combine(left, right, "These separate diagnostic locations may both need repair.")
                pairs += 1
                if pairs >= 8:
                    break
            if pairs >= 8:
                break
        if pairs >= 8:
            break
    yield from guesses
    for i in range(5):
        yield from (group[i] for group in slots if len(group) > i)
    yield from proposals
