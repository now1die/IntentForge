"""VM-owned storage, accounting and structured failures."""
from dataclasses import dataclass
from typing import Any

from compiler.ast_nodes import ASTNode

UNINITIALIZED = object()
INT_MIN, INT_MAX = -(2**31), 2**31 - 1


@dataclass
class RuntimeFault(Exception):
    code: str
    message: str
    node: ASTNode | None = None


def checked(value: int, node: ASTNode | None = None) -> int:
    if not INT_MIN <= value <= INT_MAX:
        raise RuntimeFault("INTEGER_OVERFLOW", "Signed 32-bit integer overflow.", node)
    return value


def truth(value, node):
    if type(value) is not bool:
        raise RuntimeFault("INVALID_OPERATION", "A Boolean condition is required.", node)
    return value


class WorkBudget:
    """A deterministic step budget shared by multiple vectors and programs."""

    def __init__(self, total: int):
        self.remaining = total

    def consume(self, node, count):
        if self.remaining < count:
            raise RuntimeFault("VERIFICATION_BUDGET", "Total verification step budget exhausted.", node)
        self.remaining -= count


class Environment:
    def __init__(self, parent: "Environment | None" = None):
        self.parent = parent
        self.values: dict[str, Any] = {}
        self.cells = 0

    def locate(self, name, node):
        current = self
        while current is not None:
            if name in current.values:
                return current.values, name
            current = current.parent
        raise RuntimeFault("UNINITIALIZED_VALUE", "The binding has no initialized storage.", node)


def load(location, node):
    values, key = location
    value = values[key]
    if value is UNINITIALIZED:
        raise RuntimeFault("UNINITIALIZED_VALUE", "Read before initialization.", node)
    return value
