"""Bounded specification matching. All expression checking is static."""

from __future__ import annotations

from dataclasses import dataclass
import re

from compiler.ast_nodes import (
    ArrayAccess, ASTNode, BinaryExpression, ForStatement, FunctionCall, Identifier, IfStatement, Literal,
    ReturnStatement, UnaryExpression, WhileStatement,
)
from compiler.parser import parse

from .intention_context import IntentionContext, NodeContext, ast_children


ALLOWED_EXPRESSION_NODES = (ArrayAccess, BinaryExpression, FunctionCall, Identifier, Literal, UnaryExpression)
CONDITIONALS = (IfStatement, WhileStatement, ForStatement)


class InvalidRequirement(ValueError):
    """A supplied expression or requirement field cannot be interpreted."""


@dataclass(frozen=True, slots=True)
class ExpressionTarget:
    record: NodeContext
    observed: ASTNode | None
    expected_source: str
    matches: bool
    field: str


def expression_key(node: ASTNode):
    value = node.to_dict()

    def strip(part):
        if isinstance(part, dict):
            return {key: strip(item) for key, item in part.items() if key != "span"}
        if isinstance(part, list):
            return [strip(item) for item in part]
        return part

    return strip(value)


def parse_expression(source: str) -> ASTNode:
    if len(source) > 160 or not source.strip() or re.search(r"[;{}\r\n]", source):
        raise InvalidRequirement("Provide one Mini-C expression of at most 160 characters.")
    parsed = parse(f"int requirement_probe() {{ return {source}; }}")
    if not parsed.valid or not parsed.ast:
        raise InvalidRequirement("A requirement expression is not valid Mini-C expression syntax.")
    statements = parsed.ast.functions[0].body.statements
    if len(statements) != 1 or not isinstance(statements[0], ReturnStatement) or statements[0].value is None:
        raise InvalidRequirement("A requirement must contain exactly one expression.")
    expression = statements[0].value
    stack = [expression]
    while stack:
        node = stack.pop()
        if not isinstance(node, ALLOWED_EXPRESSION_NODES):
            raise InvalidRequirement("Requirement expressions cannot contain assignment or update operations.")
        stack.extend(child for _, child in ast_children(node))
    return expression


def _description_expression(description: str) -> str | None:
    # Parse only explicit wording with named operands. A function name is never a specification.
    normalized = description.strip().rstrip(".")
    sum_match = re.fullmatch(r"return (?:the )?sum of ([A-Za-z_]\w*) and ([A-Za-z_]\w*)", normalized, re.I)
    if sum_match:
        return f"{sum_match[1]} + {sum_match[2]}"
    square = re.fullmatch(r"return (?:the )?square of ([A-Za-z_]\w*)", normalized, re.I)
    if square:
        return f"{square[1]} * {square[1]}"
    return None


def resolve_targets(context: IntentionContext) -> tuple[list[ExpressionTarget], list[str]]:
    requirement = context.requirement
    if not requirement:
        return [], []
    return_expression = requirement.return_expression or _description_expression(requirement.description or "")
    expected = {
        name: parse_expression(text)
        for name, text in (("return", return_expression), ("condition", requirement.condition))
        if text is not None
    }
    if not context.parsed.valid:
        return [], ["The requirement cannot be located without an intact AST."]
    ast = context.parsed.ast
    assert ast is not None
    functions = [function for function in ast.functions if requirement.function is None or function.name == requirement.function]
    subject_required = bool(expected or requirement.examples or requirement.function)
    if len(functions) != 1 and subject_required:
        return [], ["Select one existing function before matching the requirement."]
    notes = []
    if requirement.examples:
        if any(len(example.args) != len(functions[0].parameters) for example in requirement.examples):
            raise InvalidRequirement("Example arguments must match the selected function's arity.")
        notes.append("Input/output examples were recorded. Runtime verification is unavailable.")
    if requirement.description and not expected:
        notes.append("The description is recorded. Use an explicit return or condition expression for a static comparison.")
    if not expected:
        return [], notes
    function = functions[0]
    targets = []
    for name, expression in expected.items():
        is_return = name == "return"
        candidates = [
            record for record in context.nodes if record.function is function
            and isinstance(record.node, ReturnStatement if is_return else CONDITIONALS)
        ]
        ordinal = requirement.return_ordinal if is_return else requirement.condition_ordinal
        if ordinal is None and len(candidates) == 1:
            ordinal = 1
        if ordinal is None or not 1 <= ordinal <= len(candidates):
            notes.append(f"The {name} requirement has no unique location. Supply its one-based ordinal.")
            continue
        record = candidates[ordinal - 1]
        observed = record.node.value if is_return else record.node.condition
        text = return_expression if is_return else requirement.condition
        targets.append(ExpressionTarget(record, observed, text, observed is not None and expression_key(observed) == expression_key(expression), name))
    return targets, notes
