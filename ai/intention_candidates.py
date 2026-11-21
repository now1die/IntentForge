"""Small, evidence-grounded candidate sets for intention analysis."""

from __future__ import annotations

from dataclasses import dataclass, replace
from difflib import SequenceMatcher
from itertools import islice

from compiler.ast_nodes import (
    ArrayAccess, Assignment, BinaryExpression, FunctionCall, Identifier, Literal, ReturnStatement,
    VariableDeclaration,
)
from compiler.correction import CorrectionAction
from compiler.source_location import SourceLocation, SourceSpan
from compiler.symbol_table import Symbol, SymbolKind

from .intention_context import IntentionContext, NodeContext, overlapping
from .intention_requirements import ExpressionTarget


MAX_CANDIDATES = 24
LOCAL_SYMBOL_LIMIT = 5


@dataclass(frozen=True, slots=True)
class Evidence:
    kind: str
    detail: str
    span: SourceSpan | None = None

    def to_dict(self):
        return {"kind": self.kind, "detail": self.detail, "span": self.span.to_dict() if self.span else None}


@dataclass(frozen=True, slots=True)
class Edit:
    span: SourceSpan
    replacement: str


@dataclass(frozen=True, slots=True)
class Proposal:
    edits: tuple[Edit, ...]
    category: str
    evidence: tuple[Evidence, ...]
    assumption: str
    node_kind: str = ""
    role: str = ""
    type_match: bool = False
    references_before: int = 0
    symbol_distance: int = 0
    symbol_kind: str = ""
    specification_matches: int = 0
    in_return_position: bool = False
    counter_evidence: tuple[Evidence, ...] = ()


def point(location: SourceLocation) -> SourceSpan:
    return SourceSpan(location, location)


def apply_edits(source: str, edits: tuple[Edit, ...]) -> str:
    previous = len(source) + 1
    for edit in sorted(edits, key=lambda item: item.span.start.offset, reverse=True):
        start, end = edit.span.start.offset, edit.span.end.offset
        if not 0 <= start <= end <= len(source) or end > previous or start == previous:
            raise ValueError("Invalid or overlapping intention edits")
        source = source[:start] + edit.replacement + source[end:]
        previous = start
    return source


def _requirement_category(target: ExpressionTarget, expected_node) -> str:
    observed = target.observed
    if observed is None:
        return "MISSING_EXPRESSION"
    if isinstance(observed, BinaryExpression) and isinstance(expected_node, BinaryExpression):
        if observed.operator != expected_node.operator and target.field == "return":
            return "COMPARISON_OPERATOR" if expected_node.operator in {"==", "!=", "<", ">", "<=", ">="} else "ARITHMETIC_OPERATOR"
    if target.field == "condition":
        return "CONDITION"
    if isinstance(observed, ArrayAccess) and isinstance(expected_node, ArrayAccess):
        return "ARRAY_INDEX"
    if isinstance(observed, FunctionCall) and isinstance(expected_node, FunctionCall):
        return "FUNCTION_ARGUMENT"
    if isinstance(observed, Identifier) and isinstance(expected_node, Identifier):
        return "VARIABLE_REFERENCE"
    return "RETURN_EXPRESSION"


def _before_semicolon(context: IntentionContext, statement: ReturnStatement) -> SourceSpan | None:
    token = next((token for token in context.parsed.tokens
                  if token.type == "SEMICOLON" and statement.span.start.offset <= token.offset < statement.span.end.offset), None)
    return point(token.span.start) if token else None


def requirement_proposals(context: IntentionContext, targets: list[ExpressionTarget]):
    from .intention_requirements import parse_expression

    proposals = []
    for target in targets:
        if target.matches:
            continue
        node = target.record.node
        span = target.observed.span if target.observed is not None else None
        if span is None and isinstance(node, ReturnStatement):
            span = _before_semicolon(context, node)
        if span is None:
            continue
        proposed = target.expected_source.strip()
        replacement = f" {proposed}" if span.start == span.end else proposed
        expected_node = parse_expression(proposed)
        basis = (
            f"The supported reading of the description is {proposed!r}."
            if target.derived_from_description else f"The supplied {target.field} expression is {proposed!r}."
        )
        proposals.append(Proposal(
            (Edit(span, replacement),),
            _requirement_category(target, expected_node),
            (Evidence("OBSERVED_AST", f"Selected {target.field} belongs to function {target.record.function.name}.", node.span),
             Evidence("USER_REQUIREMENT", basis, span)),
            "The selected expression is the intended location for this requirement.",
            type(node).__name__, target.field, specification_matches=1,
        ))
    if len(proposals) > 1:
        yield combine(proposals[0], proposals[1], "Both specified expressions belong to the same requested change.")
    yield from proposals


def combine(left: Proposal, right: Proposal, assumption: str) -> Proposal:
    return Proposal(
        (*left.edits, *right.edits), "MULTIPLE_LOCALIZED", (*left.evidence, *right.evidence),
        assumption, specification_matches=left.specification_matches + right.specification_matches,
    )


def _compatible(symbol: Symbol, expected: str | None) -> bool:
    actual = symbol.type.display()
    return expected is None or actual == expected or (expected == "float" and actual == "int")


def _before_counts(context: IntentionContext, offset: int, symbol: Symbol) -> int:
    return sum(
        1 for token in context.parsed.tokens
        if token.type == "IDENTIFIER" and token.lexeme == symbol.name
        and symbol.declaration_span.end.offset <= token.offset < offset
        and context.visible_at(token.offset).get(symbol.name) is symbol
    )


def symbol_alternatives(context, record, span, expected, category, diagnostic, *, existing=""):
    offset = span.start.offset
    pool = [
        symbol for symbol in context.visible_at(offset).values()
        if symbol.name != existing and symbol.kind in {SymbolKind.PARAMETER, SymbolKind.VARIABLE}
        and _compatible(symbol, expected) and symbol.type.display() != "void"
    ]
    pool.sort(key=lambda symbol: (
        -SequenceMatcher(None, existing, symbol.name, autojunk=False).ratio() if existing else 0,
        symbol.type.display() != expected, -symbol.declaration_span.start.offset, symbol.id,
    ))
    in_return_position = record.parent_id is not None and isinstance(context.nodes[record.parent_id].node, ReturnStatement)
    for symbol in pool[:LOCAL_SYMBOL_LIMIT]:
        whitespace = " " if span.start == span.end else ""
        yield Proposal(
            (Edit(span, whitespace + symbol.name),), category,
            (Evidence("COMPILER_DIAGNOSTIC", diagnostic.message, diagnostic.span),
             Evidence("SYMBOL", f"{symbol.name} is visible here with type {symbol.type.display()}.", symbol.declaration_span)),
            f"The intended value may be the visible binding {symbol.name!r}.",
            type(record.node).__name__, record.relation or "", expected == symbol.type.display(),
            _before_counts(context, offset, symbol), max(0, offset - symbol.declaration_span.end.offset),
            symbol.kind.value, in_return_position=in_return_position,
        )


def _expected_for_identifier(context: IntentionContext, record: NodeContext) -> str | None:
    parent = context.nodes[record.parent_id].node if record.parent_id is not None else None
    node = record.node
    if isinstance(parent, ReturnStatement) and record.function:
        return record.function.return_type
    if isinstance(parent, VariableDeclaration):
        return parent.type_name
    if isinstance(parent, (Assignment, BinaryExpression)) and context.semantic:
        counterpart = (parent.target if record.relation == "value" else parent.value) if isinstance(parent, Assignment) else (
            parent.right if record.relation == "left" else parent.left
        )
        inferred = context.semantic.expression_types.get(id(counterpart))
        if inferred and not inferred.is_error:
            return inferred.display()
    if isinstance(parent, FunctionCall) and isinstance(parent.callee, Identifier):
        binding = context.visible_at(node.span.start.offset).get(parent.callee.name)
        if binding and binding.kind == SymbolKind.FUNCTION and record.relation == "arguments":
            offset = next(index for index, child in enumerate(parent.arguments) if child is node)
            if offset < len(binding.type.parameter_types):
                return binding.type.parameter_types[offset].display()
    return "int" if isinstance(parent, ArrayAccess) and record.relation == "index" else None


def semantic_proposals(context: IntentionContext):
    if not context.semantic:
        return
    for diagnostic in context.semantic.diagnostics[:MAX_CANDIDATES]:
        matches = [record for record in context.nodes if overlapping(record.node.span, diagnostic.span)]
        records = [record for record in matches if record.node.span == diagnostic.span]
        if diagnostic.code == "SEM-UNDECLARED-IDENTIFIER":
            for record in records:
                if isinstance(record.node, Identifier):
                    yield from symbol_alternatives(
                        context, record, record.node.span, _expected_for_identifier(context, record),
                        "VARIABLE_REFERENCE", diagnostic, existing=record.node.name,
                    )
        elif diagnostic.code == "SEM-INVALID-RETURN":
            for record in records:
                if not isinstance(record.node, ReturnStatement):
                    continue
                value = record.node.value
                span = value.span if value else _before_semicolon(context, record.node)
                if span and diagnostic.expected_type != "void":
                    yield from symbol_alternatives(context, record, span, diagnostic.expected_type,
                                                   "RETURN_EXPRESSION" if value else "MISSING_EXPRESSION", diagnostic)
        elif diagnostic.code in {"SEM-FUNCTION-ARG-TYPE", "SEM-TYPE-MISMATCH", "SEM-INVALID-ARRAY-INDEX"}:
            if diagnostic.expected_type not in {"bool", "char", "int", "float"}:
                continue
            for record in records[-1:]:
                node = record.node
                expression = node.initializer if isinstance(node, VariableDeclaration) else (
                    node.value if isinstance(node, Assignment) else node
                )
                if not isinstance(expression, (Identifier, Literal, BinaryExpression, FunctionCall)):
                    continue
                category = {"SEM-FUNCTION-ARG-TYPE": "FUNCTION_ARGUMENT", "SEM-INVALID-ARRAY-INDEX": "ARRAY_INDEX"}.get(
                    diagnostic.code, "DECLARATION_TYPE")
                yield from symbol_alternatives(context, record, expression.span, diagnostic.expected_type,
                                               category, diagnostic, existing=context.text(expression.span))
        elif diagnostic.code == "SEM-FUNCTION-ARG-COUNT":
            for record in records:
                if isinstance(record.node, FunctionCall):
                    yield from _argument_count(context, record, diagnostic)
        elif diagnostic.code == "SEM-NOT-CALLABLE":
            for record in records:
                node = record.node
                if not isinstance(node, Identifier) or record.parent_id is None:
                    continue
                call = context.nodes[record.parent_id].node
                binding = context.visible_at(node.span.start.offset).get(node.name)
                if isinstance(call, FunctionCall) and binding and binding.kind == SymbolKind.ARRAY and len(call.arguments) == 1:
                    yield Proposal((Edit(call.span, f"{node.name}[{context.text(call.arguments[0].span)}]"),), "ARRAY_INDEX",
                                   (Evidence("SYMBOL", f"{node.name} is declared as an array.", binding.declaration_span),
                                    Evidence("COMPILER_DIAGNOSTIC", diagnostic.message, diagnostic.span)),
                                   "The call may be an array access.", "FunctionCall", "callee")


def _argument_count(context, record, diagnostic):
    call = record.node
    args = call.arguments
    expected = int(diagnostic.expected_type)
    if len(args) == expected + 1:
        for i, param in enumerate(args[:LOCAL_SYMBOL_LIMIT]):
            if len(args) == 1:
                span = param.span
            elif i == 0:
                span = SourceSpan(param.span.start, args[1].span.start)
            else:
                span = SourceSpan(args[i - 1].span.end, param.span.end)
            yield Proposal((Edit(span, ""),), "FUNCTION_ARGUMENT",
                           (Evidence("FUNCTION_SIGNATURE", diagnostic.message, diagnostic.span),
                            Evidence("OBSERVED_AST", f"The call's argument {i + 1} occupies this span.", param.span)),
                           "This argument may be extra. Removing it can change the call's behavior.", "FunctionCall", "arguments")
    elif len(args) + 1 == expected and isinstance(call.callee, Identifier):
        symbol = context.visible_at(call.span.start.offset).get(call.callee.name)
        if symbol and symbol.kind == SymbolKind.FUNCTION:
            closing = next((token for token in reversed(context.parsed.tokens)
                            if token.span.end == call.span.end and token.type == "RPAREN"), None)
            if closing:
                for proposal in symbol_alternatives(context, record, point(closing.span.start),
                                                    symbol.type.parameter_types[-1].display(), "FUNCTION_ARGUMENT", diagnostic):
                    if args:
                        edit = proposal.edits[0]
                        yield replace(proposal, edits=(replace(edit, replacement="," + edit.replacement),))
                    else:
                        yield proposal


def compiler_proposals(context: IntentionContext):
    for diagnostic in context.parsed.syntax_errors[:4]:
        for candidate in diagnostic.correction_candidates[:5]:
            edits = tuple(Edit(edit.span, "" if edit.action == CorrectionAction.DELETE else edit.text)
                          for edit in candidate.edits or (candidate,))
            yield Proposal(edits, "COMPILER_RECOVERY",
                           (Evidence("COMPILER_DIAGNOSTIC", diagnostic.message, diagnostic.span),),
                           candidate.reason, "Token", diagnostic.grammar_context or "")


def candidate_stream(context: IntentionContext, targets: list[ExpressionTarget]):
    yield from requirement_proposals(context, targets)
    semantic = list(islice(semantic_proposals(context), MAX_CANDIDATES))
    # Reserve a few compound choices. Every component needs its own evidence.
    if len(context.diagnostics) > 1:
        combinations = 0
        for i, left in enumerate(semantic):
            for right in semantic[i + 1:]:
                a, b = left.edits[0].span, right.edits[0].span
                if a.start != b.start and not overlapping(a, b):
                    yield combine(left, right, "These independent diagnostics may both need correction.")
                    combinations += 1
                    if combinations == 3:
                        break
            if combinations == 3:
                break
    yield from semantic
    yield from compiler_proposals(context)
