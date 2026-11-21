"""Bounded, typed requirements for Phase 8.

Inputs without an expected value describe coverage only. Runtime observations
and fixture holdouts use separate contracts.
"""
from dataclasses import dataclass
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, StrictBool, StrictInt, model_validator

from .behavior_oracle import program_identity
from .guided_evidence import conflicting_expectations

INT_MIN = -(2**31)
INT_MAX = 2**31 - 1
Integer = Annotated[StrictInt, Field(ge=INT_MIN, le=INT_MAX)]
Scalar = Integer | StrictBool
Input = Annotated[tuple[Scalar, ...], Field(max_length=16)]
PartialInputs = Annotated[tuple[Input, ...], Field(max_length=12)]


class Bounds(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    minimum: Integer
    maximum: Integer

    @model_validator(mode="after")
    def ordered(self):
        if self.minimum > self.maximum:
            raise ValueError("An input interval must be in increasing order.")
        return self


Domain = Annotated[tuple[Bounds | None, ...], Field(max_length=16)]


class InvalidSpecification(ValueError):
    """A supplied requirement contradicts its selected function or domain."""


def includes_input(bounds, values):
    if bounds is None:
        return True
    return len(bounds) == len(values) and all(
        axis is None or type(value) is int and axis.minimum <= value <= axis.maximum
        for axis, value in zip(bounds, values, strict=True)
    )


def typed(value, kind):
    if kind == "bool":
        return type(value) is bool
    return kind == "int" and type(value) is int and INT_MIN <= value <= INT_MAX


@dataclass(frozen=True, slots=True)
class Specification:
    function: str | None
    parameters: tuple[tuple[str, str], ...]
    return_type: str | None
    examples: tuple
    partial: tuple
    bounds: tuple | None
    source_snapshot: str
    status: str

    def summary(self):
        return {
            "function": self.function,
            "parameters": [{"name": name, "type": kind} for name, kind in self.parameters],
            "return_type": self.return_type,
            "status": self.status,
            "source_snapshot": self.source_snapshot,
            "provenance": "SUPPLIED_EXPECTATIONS" if self.examples else "UNSPECIFIED",
            "trusted_examples": len(self.examples),
            "partial_inputs": len(self.partial),
            "input_domain": [axis.model_dump() if axis is not None else None for axis in self.bounds]
            if self.bounds is not None else None,
            "assumptions": ["Checked signed 32-bit arithmetic", "Integer division truncates toward zero",
                            "Expectations constrain only the supplied inputs"],
        }


def specification(context, entry, examples, bounds, partial):
    identity = program_identity(context.source)
    if not context.compiler_valid:
        return Specification(entry, (), None, (), (), bounds, identity, "INCOMPLETE_COMPILER_EVIDENCE")
    if conflicting_expectations((row.args, row.expected_return) for row in examples):
        raise InvalidSpecification("The same input has conflicting expected outputs.")
    if entry is None:
        if examples or bounds is not None or partial:
            raise InvalidSpecification("Select a function for the specification.")
        return Specification(None, (), None, (), (), None, identity, "INCOMPLETE_SPECIFICATION")
    function = next((candidate for candidate in context.parsed.ast.functions if candidate.name == entry), None)
    if function is None:
        raise InvalidSpecification("The specification function does not exist.")
    params = tuple((param.name, param.type_name) for param in function.parameters)
    if function.return_type not in {"int", "bool"} or any(kind not in {"int", "bool"} for _, kind in params):
        return Specification(entry, params, function.return_type, (), tuple(partial), bounds, identity, "UNSUPPORTED_SIGNATURE")
    if bounds is not None and (len(bounds) != len(params) or any(
        axis is not None and kind != "int" for axis, (_, kind) in zip(bounds, params)
    )):
        raise InvalidSpecification("Supply one domain axis per parameter, using null for Boolean parameters.")
    for values in (*[row.args for row in examples], *partial):
        if len(values) != len(params) or not all(typed(value, kind) for value, (_, kind) in zip(values, params)):
            raise InvalidSpecification("A specification input does not match the function's arity or scalar types.")
        if not includes_input(bounds, values):
            raise InvalidSpecification("A specification input lies outside the declared domain.")
    if any(not typed(row.expected_return, function.return_type) for row in examples):
        raise InvalidSpecification("An expected output does not match the function's scalar return type.")
    return Specification(entry, params, function.return_type, tuple(examples), tuple(partial), bounds, identity,
                         "VALIDATED_EXAMPLES" if examples else "INCOMPLETE_SPECIFICATION")
