"""Versioned local gateway and private worker messages."""
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator

from ai.behavior_oracle import BehaviorResult, ExecutionLimits, RuntimeIssue
from ai.guided_evidence import OriginalEvidence, ReviewEvidence, conflicting_expectations
from ai.specification import Domain, includes_input

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
    vectors: tuple[TestVector, ...] = Field(max_length=12)
    engine_version: Literal[4, 5, 55, 6, 65, 7, 75, 8, 85, 9, 95, 10] = 4
    limits: LocalLimits = Field(default_factory=LocalLimits)
    trace: bool = Field(default=False, strict=True)
    compare_candidates: bool = Field(default=False, strict=True)
    return_expression: str | None = Field(default=None, min_length=1, max_length=160)
    condition: str | None = Field(default=None, min_length=1, max_length=160)
    input_domain: Domain | None = None

    @model_validator(mode="after")
    def limits_and_source(self):
        if len(self.source.encode()) > 48_000:
            raise ValueError("Local execution admission limits exceeded")
        if not self.vectors and (self.engine_version not in {5, 55, 6, 65, 7, 75, 8, 85, 9, 95, 10} or not self.compare_candidates):
            raise ValueError("Supply a test vector or explicitly request Phase 5 observational comparison")
        if self.engine_version in {7, 75, 8, 85, 9, 95, 10} and conflicting_expectations((row.arguments, row.expected) for row in self.vectors):
            raise ValueError("The same input has conflicting expected outputs.")
        if "input_domain" in self.model_fields_set and self.engine_version not in {8, 85, 9, 95, 10}:
            raise ValueError("Input domains require Phase 8.")
        if any(not includes_input(self.input_domain, row.arguments) for row in self.vectors):
            raise ValueError("A test input lies outside the declared domain.")
        return self


class Program(Message):
    source: Source
    candidate_id: CandidateId | None = None


class Batch(Message):
    entry_point: Entry
    vectors: tuple[TestVector, ...] = Field(max_length=12)
    engine_version: Literal[4, 5, 7, 8] = 4
    input_domain: Domain | None = None
    limits: LocalLimits
    trace: bool = Field(strict=True)
    programs: tuple[Program, ...] = Field(min_length=1, max_length=5)

    @model_validator(mode="after")
    def enforce(self):
        if not self.vectors and self.engine_version not in {5, 7, 8}:
            raise ValueError("Legacy verification needs an expected result")
        if self.programs[0].candidate_id is not None or any(row.candidate_id is None for row in self.programs[1:]):
            raise ValueError("Supply the original followed by identified candidates")
        if len({row.candidate_id for row in self.programs}) != len(self.programs):
            raise ValueError("Candidate identities must be distinct")
        if self.input_domain is not None and self.engine_version != 8:
            raise ValueError("Private input domains require profile 8.")
        if any(not includes_input(self.input_domain, row.arguments) for row in self.vectors):
            raise ValueError("Private test input lies outside the declared domain.")
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


class RankedProbe(Probe):
    assessment: Literal["different_values", "candidate_runtime_failure", "candidate_execution_limit",
                        "same_values", "insufficient_observations"]
    separated_pairs: int = Field(ge=0, le=6)
    new_pairs: int = Field(ge=0, le=6)
    steps: int = Field(ge=0, le=80_000)
    input_basis: Literal["boundary", "combination", "scalar_seed"]


class BatchResult(Message):
    runs: tuple[BehaviorResult, ...] = Field(min_length=1, max_length=5)
    probes: tuple[RankedProbe | Probe, ...] = Field(default=(), max_length=8)


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
    probes: tuple[RankedProbe | Probe, ...] = ()
    requires_approval: Literal[True] = True



class GuidedEvidence(Message):
    original: OriginalEvidence
    review: ReviewEvidence
    confirmed_fault: bool
    recommended_candidate: CandidateId | None
    matching_candidates: tuple[CandidateId, ...]


class CandidatePair(Message):
    candidates: tuple[CandidateId, CandidateId]
    status: Literal["distinguished", "agreed_on_probes", "inconclusive", "untested"]
    compared_inputs: int = Field(ge=0, le=8)


class Phase7Response(VerifyResponse):
    guided_evidence: GuidedEvidence
    candidate_pairs: tuple[CandidatePair, ...] = Field(default=(), max_length=6)
    candidate_categories: dict[CandidateId, str] = Field(default_factory=dict)



class Phase8Response(Phase7Response):
    review_presentation: Literal["OPTIONAL_COLLAPSED", "REVIEW_VISIBLE"]
    specification: dict | None = None
    candidate_details: dict[CandidateId, dict] = Field(default_factory=dict)


class RuntimeAlternative(Message):
    completed_trusted_suite: bool
    matched_trusted_suite: bool


class RuntimeObservation(Message):
    issue: RuntimeIssue
    program: str
    input: tuple[Scalar, ...] | None
    alternatives: dict[CandidateId, RuntimeAlternative]


class Phase9Response(Phase8Response):
    semantic_profile: Literal[9, 95, 10]
    runtime_observation: RuntimeObservation | None = None
