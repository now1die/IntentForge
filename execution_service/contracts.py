"""Versioned local gateway and private worker messages."""
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator

from ai.behavior_oracle import BehaviorResult, ExecutionLimits

Source = Annotated[str, StringConstraints(max_length=24_000)]
Entry = Annotated[str, StringConstraints(pattern=r"^[A-Za-z_][A-Za-z_0-9]{0,79}$")]
Scalar = Annotated[int, Field(strict=True, ge=-(2**31), le=2**31-1)] | Annotated[bool, Field(strict=True)]
CandidateId = Annotated[str, StringConstraints(pattern=r"^IR-[0-9a-f]{12}$")]


class Message(BaseModel):
    model_config = ConfigDict(extra="forbid")


class LocalLimits(ExecutionLimits):
    steps: int = Field(default=10_000, strict=True, ge=1, le=20_000)
    call_depth: int = Field(default=32, strict=True, ge=1, le=64)
    memory_cells: int = Field(default=4096, strict=True, ge=1, le=8192)


class TestVector(Message):
    arguments: tuple[Scalar, ...] = Field(max_length=16)
    expected: Scalar


class VerifyRequest(Message):
    language: Literal["mini-c"] = "mini-c"
    source: Source
    entry_point: Entry
    vectors: tuple[TestVector, ...] = Field(min_length=1, max_length=12)
    limits: LocalLimits = Field(default_factory=LocalLimits)
    trace: bool = Field(default=False, strict=True)
    compare_candidates: bool = Field(default=False, strict=True)
    return_expression: str | None = Field(default=None, min_length=1, max_length=160)
    condition: str | None = Field(default=None, min_length=1, max_length=160)

    @model_validator(mode="after")
    def limits_and_source(self):
        if len(self.source.encode()) > 48_000:
            raise ValueError("Local execution admission limits exceeded")
        return self


class Program(Message):
    source: Source
    candidate_id: CandidateId | None = None


class Batch(Message):
    entry_point: Entry
    vectors: tuple[TestVector, ...] = Field(min_length=1, max_length=12)
    limits: LocalLimits
    trace: bool = Field(strict=True)
    programs: tuple[Program, ...] = Field(min_length=1, max_length=5)

    @model_validator(mode="after")
    def enforce(self):
        if self.programs[0].candidate_id is not None or any(row.candidate_id is None for row in self.programs[1:]):
            raise ValueError("Supply the original followed by identified candidates")
        if len({row.candidate_id for row in self.programs}) != len(self.programs):
            raise ValueError("Candidate identities must be distinct")
        if any(len(row.source.encode()) > 48_000 for row in self.programs):
            raise ValueError("Source byte limit exceeded")
        return self


class ProbeResult(Message):
    candidate_id: CandidateId
    status: Literal["observed", "runtime_failure", "execution_limited", "unsupported"]
    actual: Scalar | None = None
    issue: str | None = Field(default=None, max_length=40)


class Probe(Message):
    arguments: tuple[Scalar, ...] = Field(max_length=16)
    relation: Literal["agree", "disagree", "inconclusive"]
    candidates: tuple[ProbeResult, ...] = Field(max_length=4)


class BatchResult(Message):
    runs: tuple[BehaviorResult, ...] = Field(min_length=1, max_length=5)
    probes: tuple[Probe, ...] = Field(default=(), max_length=8)


class Availability(Message):
    status: Literal["available", "disabled", "unsupported_environment", "worker_unavailable",
                    "worker_unhealthy", "capacity_reached", "deadline_exceeded"]
    detail: str
    boundary: Literal["isolated-local-v1"] | None = None


class CandidateReview(Message):
    id: CandidateId
    static_rank: int
    source: Source
    compiler_valid: bool
    static_evidence: str
    hypothesis: str
    behavior: BehaviorResult | None = None


class VerifyResponse(Message):
    availability: Availability
    program: str
    entry_point: Entry
    original: BehaviorResult | None = None
    candidates: tuple[CandidateReview, ...] = ()
    review_order: tuple[CandidateId, ...] = ()
    comparison_status: Literal["MULTIPLE_MATCHES", "ONE_MATCH", "NO_OBSERVED_MATCH"] | None = None
    probes: tuple[Probe, ...] = ()
    requires_approval: Literal[True] = True
