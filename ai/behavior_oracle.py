"""Versioned contract for trusted Mini-C execution evidence."""
from enum import StrEnum
from hashlib import sha256
from typing import Literal, Protocol

from pydantic import BaseModel, ConfigDict, Field, StrictBool, StrictInt, model_validator

from analysis_evidence.contract import Span

Scalar = StrictInt | StrictBool


def program_identity(source: str) -> str:
    return sha256(source.encode()).hexdigest()


class Status(StrEnum):
    ORACLE_UNAVAILABLE = "ORACLE_UNAVAILABLE"
    EXECUTION_UNSUPPORTED = "EXECUTION_UNSUPPORTED"
    EXECUTION_LIMITED = "EXECUTION_LIMITED"
    BEHAVIOR_UNKNOWN = "BEHAVIOR_UNKNOWN"
    MATCHES_SUPPLIED_TESTS = "MATCHES_SUPPLIED_TESTS"
    MISMATCHES_SUPPLIED_TESTS = "MISMATCHES_SUPPLIED_TESTS"


class ExecutionLimits(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    steps: int = Field(default=10_000, ge=1, le=1_000_000)
    call_depth: int = Field(default=32, ge=1, le=128)
    memory_cells: int = Field(default=4096, ge=1, le=65_536)


class Vector(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    arguments: tuple[Scalar, ...] = Field(max_length=16)
    expected: Scalar


class Observation(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    vector: Vector
    actual: Scalar

    def matches(self) -> bool:
        return type(self.actual) is type(self.vector.expected) and self.actual == self.vector.expected


class TraceEvent(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    kind: Literal["FUNCTION_ENTER", "FUNCTION_RETURN", "DECLARATION", "ASSIGNED", "ARRAY_UPDATED",
                  "CONDITION_TRUE", "CONDITION_FALSE", "LOOP_ITERATION", "RUNTIME_ERROR", "EXECUTION_LIMIT"]
    vector: int = Field(ge=0, lt=12)
    step: int = Field(ge=0)
    span: Span | None = None


class RuntimeIssue(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    code: str = Field(max_length=40)
    message: str = Field(max_length=240)
    vector: int | None = Field(default=None, ge=0, lt=12)
    span: Span | None = None


class ExecutionSample(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    steps: int = Field(ge=0)
    peak_cells: int = Field(ge=0)
    call_depth: int = Field(ge=0)


class ExecutionDetails(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    provider: Literal["mini-c-vm"] = "mini-c-vm"
    vectors: tuple[Vector, ...] = Field(max_length=12)
    samples: tuple[ExecutionSample, ...] = Field(max_length=12)
    issue: RuntimeIssue | None = None
    trace: tuple[TraceEvent, ...] = Field(default=(), max_length=64)
    trace_truncated: bool = False


class BehaviorResult(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    schema_version: Literal[1] = 1
    program: str = Field(pattern=r"^[0-9a-f]{64}$")
    entry_point: str = Field(pattern=r"^[A-Za-z_][A-Za-z_0-9]{0,79}$")
    candidate_id: str | None = Field(default=None, max_length=64)
    status: Status
    observations: tuple[Observation, ...] = Field(default=(), max_length=12)
    diagnostics: tuple[str, ...] = Field(default=(), max_length=12)
    unsupported: tuple[str, ...] = Field(default=(), max_length=12)
    execution: ExecutionDetails | None = None

    @model_validator(mode="after")
    def check_results(self):
        if self.status == Status.MATCHES_SUPPLIED_TESTS and (
            not self.observations or not all(row.matches() for row in self.observations)
        ):
            raise ValueError("A match needs observed values for matching test vectors.")
        if self.status == Status.MISMATCHES_SUPPLIED_TESTS and (
            not self.observations or all(row.matches() for row in self.observations)
        ):
            raise ValueError("A mismatch needs an observed counterexample.")
        if self.execution is not None:
            expected = tuple(row.model_dump_json() for row in self.execution.vectors)
            observed = tuple(row.vector.model_dump_json() for row in self.observations)
            if observed != expected[:len(observed)] or len(self.execution.samples) < len(observed):
                raise ValueError("VM observations must map to executed supplied vectors.")
            if self.status in {Status.MATCHES_SUPPLIED_TESTS, Status.MISMATCHES_SUPPLIED_TESTS}:
                if (self.execution.issue is not None or observed != expected
                        or len(self.execution.samples) != len(expected)):
                    raise ValueError("A completed verification needs results for every supplied vector.")
        return self


class BehaviorOracle(Protocol):
    def verify(
        self, source: str, entry_point: str, vectors: tuple[Vector, ...], limits: ExecutionLimits,
        *, candidate_id: str | None = None,
    ) -> BehaviorResult: ...
