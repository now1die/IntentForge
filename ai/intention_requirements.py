"""Bounded specification matching. All expression checking is static."""

from __future__ import annotations

from dataclasses import dataclass
import re

from compiler.ast_nodes import (
    ArrayAccess, ASTNode, BinaryExpression, Block, ForStatement, FunctionCall, FunctionDefinition,
    Identifier, IfStatement, Literal, ReturnStatement, UnaryExpression, VariableDeclaration, WhileStatement,
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
    derived_from_description: bool


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


def _domain_description(description: str, function: FunctionDefinition) -> dict[str, str]:
    text = description.casefold().strip().rstrip(".")
    parameter_names = {parameter.name for parameter in function.parameters}
    if text in {"return total cost", "return the total cost"} and {"price", "quantity"} <= parameter_names:
        matches = []
        for statement in function.body.statements:
            product = statement.initializer if isinstance(statement, VariableDeclaration) else None
            if (isinstance(product, BinaryExpression) and product.operator == "*"
                    and isinstance(product.left, Identifier) and isinstance(product.right, Identifier)
                    and {product.left.name, product.right.name} == {"price", "quantity"}):
                matches.append(statement.name)
        return {"return": matches[0]} if len(matches) == 1 else {}

    threshold = re.fullmatch(r"eligibility begins at ([0-9]{1,5})", text)
    if threshold and len(function.parameters) == 1 and function.parameters[0].name == "age" and function.parameters[0].type_name == "int":
        matching = []
        for statement in function.body.statements:
            if not isinstance(statement, IfStatement):
                continue
            guard = statement.condition
            branch = statement.then_branch
            if isinstance(branch, Block) and len(branch.statements) == 1:
                branch = branch.statements[0]
            if (isinstance(guard, BinaryExpression) and isinstance(guard.left, Identifier)
                    and guard.left.name == "age" and isinstance(guard.right, Literal)
                    and guard.right.literal_type == "int"
                    and isinstance(branch, ReturnStatement) and isinstance(branch.value, Literal)
                    and branch.value.literal_type in {"int", "bool"} and branch.value.value in (True, 1)):
                matching.append(statement)
        if len(matching) == 1:
            return {"condition": f"age >= {int(threshold[1])}"}
    return {}


def resolve_targets(context: IntentionContext) -> tuple[list[ExpressionTarget], list[str]]:
    requirement = context.requirement
    if not requirement:
        return [], []
    explicit = {name: text for name, text in (("return", requirement.return_expression),
                                               ("condition", requirement.condition)) if text is not None}
    expected = {name: (text, parse_expression(text), False) for name, text in explicit.items()}
    if not context.parsed.valid:
        return [], ["The requirement cannot be located without an intact AST."]
    ast = context.parsed.ast
    assert ast is not None
    functions = [function for function in ast.functions if requirement.function is None or function.name == requirement.function]
    subject_required = bool(expected or requirement.description or requirement.examples or requirement.function)
    if len(functions) != 1 and subject_required:
        return [], ["Select one existing function before matching the requirement."]
    notes = []
    if requirement.examples:
        if any(len(example.args) != len(functions[0].parameters) for example in requirement.examples):
            raise InvalidRequirement("Example arguments must match the selected function's arity.")
        notes.append("Input/output examples were recorded. Runtime verification is unavailable.")
    if requirement.description and functions:
        derived = _domain_description(requirement.description, functions[0])
        named_expression = _description_expression(requirement.description)
        if named_expression:
            derived["return"] = named_expression
        for name, text in derived.items():
            if name not in expected:
                expected[name] = (text, parse_expression(text), True)
        if not expected:
            notes.append("The description is recorded. Use an explicit return or condition expression for a static comparison.")
    if not expected:
        return [], notes
    function = functions[0]
    targets = []
    for name, (text, expression, derived) in expected.items():
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
        matches = observed is not None and expression_key(observed) == expression_key(expression)
        targets.append(ExpressionTarget(record, observed, text, matches, name, derived))
    return targets, notes
