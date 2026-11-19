"""A constrained description grammar with an explicit abstention result."""

from dataclasses import dataclass
import re

from compiler.ast_nodes import BinaryExpression, Block, Identifier, IfStatement, ReturnStatement

from .intention_context import IntentionContext


ATOM = r"(?:[A-Za-z_][A-Za-z_0-9]*|-?\d{1,8}|true|false)"
COMPARATORS = {
    "at least": ">=", "at most": "<=", "greater than": ">", "less than": "<",
    "equal to": "==", "different from": "!=", "not equal to": "!=",
}
OPERATIONS = {
    "sum": "+", "product": "*", "difference": "-", "quotient": "/", "remainder": "%",
}


@dataclass(frozen=True, slots=True)
class NormalizedRequirement:
    subject: str
    operation: str
    operands: tuple[str, ...]
    expression: str
    condition_ordinal: int | None = None


def _predicate(text: str):
    alternatives = "|".join(re.escape(item) for item in COMPARATORS)
    match = re.fullmatch(fr"({ATOM}) is ({alternatives}) ({ATOM})", text, re.I)
    if match:
        left, word, right = match.groups()
        operator = COMPARATORS[word.lower()]
        return operator, (left, right), f"{left} {operator} {right}"
    if re.fullmatch(r"[A-Za-z_][A-Za-z_0-9]*", text):
        return "truth", (text,), text
    return None


def _minmax(context, function, operation, left, right):
    functions = [row.node for row in context.nodes
                 if row.node is row.function and (function is None or row.function.name == function)]
    if len(functions) != 1 or len(functions[0].body.statements) != 2 or left == right:
        return None
    branch, tail = functions[0].body.statements
    if not isinstance(branch, IfStatement) or branch.else_branch is not None or not isinstance(tail, ReturnStatement):
        return None
    affirmative = branch.then_branch
    if isinstance(affirmative, Block) and len(affirmative.statements) == 1:
        affirmative = affirmative.statements[0]
    if not isinstance(affirmative, ReturnStatement) or not all(isinstance(row.value, Identifier) for row in (affirmative, tail)):
        return None
    first, second = affirmative.value.name, tail.value.name
    guard = branch.condition
    if {first, second} != {left, right} or not isinstance(guard, BinaryExpression):
        return None
    if not all(isinstance(node, Identifier) for node in (guard.left, guard.right)) or {
        guard.left.name, guard.right.name
    } != {left, right}:
        return None
    operator = "<" if operation == "minimum" else ">"
    if guard.left.name != first:
        operator = ">" if operator == "<" else "<"
    if guard.operator in {"<=", ">="}:
        operator += "="
    return NormalizedRequirement("condition", operation, (first, second),
                                 f"{guard.left.name} {operator} {guard.right.name}", 1)


def normalize_description(description: str, context: IntentionContext, function: str | None, *, generalized=False):
    text = " ".join(description.strip().rstrip(".").split())
    if generalized:
        cell = re.fullmatch(fr"return (?:the )?element of ([A-Za-z_][A-Za-z_0-9]*) at index ({ATOM})", text, re.I)
        if cell:
            return NormalizedRequirement("return", "array element", (cell[1], cell[2]), f"{cell[1]}[{cell[2]}]")
        accumulator = re.fullmatch(fr"return (?:the )?accumulator ([A-Za-z_][A-Za-z_0-9]*) (plus|minus) ({ATOM})", text, re.I)
        if accumulator:
            operator = "+" if accumulator[2].lower() == "plus" else "-"
            return NormalizedRequirement("return", "accumulator result", (accumulator[1], accumulator[3]),
                                         f"{accumulator[1]} {operator} ({accumulator[3]})")
    arithmetic = re.fullmatch(fr"return (?:the )?({'|'.join(OPERATIONS)}) (?:of|between) ({ATOM}) and ({ATOM})", text, re.I)
    if arithmetic:
        name, left, right = arithmetic.groups()
        return NormalizedRequirement("return", name.lower(), (left, right), f"{left} {OPERATIONS[name.lower()]} {right}")
    adjustment = re.fullmatch(fr"return ({ATOM}) (incremented|decremented) by ({ATOM})", text, re.I)
    if adjustment:
        left, name, right = adjustment.groups()
        operator = "+" if name.lower() == "incremented" else "-"
        return NormalizedRequirement("return", name.lower(), (left, right), f"{left} {operator} ({right})")
    value = re.fullmatch(fr"return (?:the )?value of ({ATOM})", text, re.I)
    if value:
        return NormalizedRequirement("return", "value", (value[1],), value[1])
    call = re.fullmatch(fr"return the result of calling ([A-Za-z_][A-Za-z_0-9]*) with ({ATOM}(?: and {ATOM}){{0,3}})", text, re.I)
    if call:
        args = tuple(re.split(" and ", call[2], flags=re.I))
        return NormalizedRequirement("return", "call", (call[1], *args), f"{call[1]}({', '.join(args)})")
    choice = re.fullmatch(fr"return (?:the )?(minimum|maximum) of ({ATOM}) and ({ATOM})", text, re.I)
    if choice:
        return _minmax(context, function, choice[1].lower(), choice[2], choice[3])
    prefixed = re.fullmatch(r"(return whether|test whether) (.+)", text, re.I)
    if not prefixed:
        return None
    subject = "return" if prefixed[1].lower() == "return whether" else "condition"
    body = prefixed[2]
    bounds = re.fullmatch(fr"({ATOM}) is between ({ATOM}) and ({ATOM}) inclusive", body, re.I)
    if generalized and not bounds:
        exclusive = re.fullmatch(fr"({ATOM}) is between ({ATOM}) and ({ATOM}) exclusive", body, re.I)
        if exclusive:
            value, lower, upper = exclusive.groups()
            return NormalizedRequirement(subject, "exclusive range", (value, lower, upper),
                                         f"{value} > {lower} && {value} < {upper}")
        negate = re.fullmatch(r"not \((.+)\)", body, re.I)
        pred = _predicate(negate[1]) if negate else None
        if pred:
            return NormalizedRequirement(subject, "negation", pred[1], f"!({pred[2]})")
    if bounds:
        value, lower, upper = bounds.groups()
        return NormalizedRequirement(subject, "inclusive range", (value, lower, upper),
                                     f"{value} >= {lower} && {value} <= {upper}")
    logic = re.fullmatch(r"both (.+) and (.+)|either (.+) or (.+)", body, re.I)
    if logic:
        left_text, right_text = logic.groups()[:2] if logic[1] else logic.groups()[2:]
        left, right = _predicate(left_text), _predicate(right_text)
        if left and right:
            operator = "&&" if logic[1] else "||"
            return NormalizedRequirement(subject, operator, (*left[1], *right[1]), f"({left[2]}) {operator} ({right[2]})")
        return None
    single = _predicate(body)
    if single:
        return NormalizedRequirement(subject, single[0], single[1], single[2])
    return None
