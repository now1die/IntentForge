"""Normalize atomic integer comparisons without rewriting evaluation order."""
from dataclasses import dataclass

from compiler import ast_nodes as ast

REVERSE = {"<": ">", "<=": ">=", ">": "<", ">=": "<=", "==": "==", "!=": "!="}
NEGATE = {"<": ">=", "<=": ">", ">": "<=", ">=": "<", "==": "!=", "!=": "=="}
INT_MIN, INT_MAX = -(2**31), 2**31 - 1


@dataclass(frozen=True, slots=True)
class Comparison:
    left: ast.ASTNode
    operator: str
    right: ast.ASTNode


def normalized_comparison(expression, expression_types, bindings, *, preferred=None):
    """Return a semantic view of a pure comparison with original operand spans."""
    negate = isinstance(expression, ast.UnaryExpression) and expression.operator == "!"
    node = expression.operand if negate else expression
    if not isinstance(node, ast.BinaryExpression) or node.operator not in REVERSE:
        return None

    def key(operand):
        inferred = expression_types.get(id(operand))
        if inferred is None or inferred.display() != "int":
            return None
        if isinstance(operand, ast.Identifier):
            symbol = bindings.get(id(operand))
            return (0 if symbol.id == preferred else 1, symbol.id) if symbol else None
        if isinstance(operand, ast.Literal) and type(operand.value) is int and INT_MIN <= operand.value <= INT_MAX:
            return (2, operand.value)
        return None

    left, right = key(node.left), key(node.right)
    if left is None or right is None:
        return None
    operator = NEGATE[node.operator] if negate else node.operator
    if left > right:
        return Comparison(node.right, REVERSE[operator], node.left)
    return Comparison(node.left, operator, node.right)
