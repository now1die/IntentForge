"""Mini-C's checked integer and Boolean operations."""
import operator

from .runtime import RuntimeFault, checked

RELATIONS = {"<": operator.lt, "<=": operator.le, ">": operator.gt, ">=": operator.ge}
INTEGER = {"+": operator.add, "-": operator.sub, "*": operator.mul}


def binary(symbol, left, right, node):
    if symbol in {"==", "!="} and type(left) is type(right) and type(left) in {int, bool}:
        return (left == right) == (symbol == "==")
    if type(left) is not int or type(right) is not int:
        raise RuntimeFault("INVALID_OPERATION", "Operator requires integer operands.", node)
    if symbol in RELATIONS:
        return RELATIONS[symbol](left, right)
    if symbol in INTEGER:
        return checked(INTEGER[symbol](left, right), node)
    if symbol in {"/", "%"}:
        if right == 0:
            raise RuntimeFault("DIVISION_BY_ZERO", "Division or remainder by zero.", node)
        quotient = abs(left) // abs(right)
        if (left < 0) != (right < 0):
            quotient = -quotient
        checked(quotient, node)
        return quotient if symbol == "/" else left - quotient * right
    raise RuntimeFault("INVALID_OPERATION", "Unsupported integer operation.", node)
