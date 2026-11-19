"""Contracts for finite behavioral observations. The project ships no Mini-C executor."""

from dataclasses import asdict, dataclass
from enum import StrEnum
from typing import Any, Protocol


class BehaviorStatus(StrEnum):
    VERIFIED = "BEHAVIOR_VERIFIED"
    MISMATCH = "BEHAVIOR_MISMATCH"
    UNVERIFIED = "BEHAVIOR_UNVERIFIED"
    ORACLE_UNAVAILABLE = "ORACLE_UNAVAILABLE"
    EXECUTION_UNSUPPORTED = "EXECUTION_UNSUPPORTED"


@dataclass(frozen=True)
class Example:
    args: tuple[int | bool, ...]
    expected_return: int | bool


@dataclass(frozen=True)
class BehaviorSpec:
    entry: str
    tests: tuple[Example, ...]

    @classmethod
    def from_dict(cls, data):
        entry = data["entry"]
        tests = data["tests"]
        if not isinstance(entry, str) or not entry.isidentifier() or not isinstance(tests, list) or not tests:
            raise ValueError("Behavior examples need an entry identifier and at least one input vector")
        examples = []
        for test in tests:
            args, expected = test["args"], test["expected_return"]
            if not isinstance(args, list) or any(type(value) not in {int, bool} for value in [*args, expected]):
                raise ValueError("Behavior examples accept integer and Boolean inputs and returns")
            examples.append(Example(tuple(args), expected))
        return cls(entry, tuple(examples))


class BehaviorOracle(Protocol):
    def observe(self, source: str, specification: BehaviorSpec, *, timeout_seconds: float) -> tuple[Any, ...]:
        """Return observations in vector order; enforce the timeout at the execution boundary."""


@dataclass(frozen=True)
class BehaviorResult:
    status: BehaviorStatus
    passed: int = 0
    observed: int = 0
    specified: int = 0
    reason: str | None = None

    def to_dict(self):
        return asdict(self)


def verify_behavior(source, spec, *, compiler_valid, supported, oracle=None, timeout_seconds=1.0):
    if not supported or (source is not None and not compiler_valid):
        return BehaviorResult(BehaviorStatus.EXECUTION_UNSUPPORTED, reason="Language or source is unsupported")
    if source is None or spec is None:
        return BehaviorResult(BehaviorStatus.UNVERIFIED, reason="No candidate or executable input/output specification")
    count = len(spec.tests)
    if oracle is None:
        return BehaviorResult(BehaviorStatus.ORACLE_UNAVAILABLE, specified=count, reason="No isolated Mini-C executor configured")
    if timeout_seconds <= 0:
        raise ValueError("The timeout must be positive")
    try:
        actual = oracle.observe(source, spec, timeout_seconds=timeout_seconds)
        if not isinstance(actual, tuple) or len(actual) != count:
            raise ValueError("Invalid observation count or payload")
        passed = sum(
            type(value) is type(example.expected_return) and value == example.expected_return
            for value, example in zip(actual, spec.tests, strict=True)
        )
    except TimeoutError:
        return BehaviorResult(BehaviorStatus.UNVERIFIED, specified=count, reason="Oracle timed out")
    except Exception as exc:
        return BehaviorResult(BehaviorStatus.UNVERIFIED, specified=count, reason=f"Oracle failed ({type(exc).__name__})")
    status = BehaviorStatus.VERIFIED if passed == count else BehaviorStatus.MISMATCH
    return BehaviorResult(status, passed, count, count)
