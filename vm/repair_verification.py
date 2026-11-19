"""Opt-in trusted comparison. Static candidates stay in their original order."""
from dataclasses import dataclass

from ai.behavior_oracle import BehaviorResult, ExecutionLimits, Status, Vector
from ai.intention_context import Requirement
from ai.intention_engine import IntentionResult, analyze_intention

from .behavioral_executor import MiniCOracle, ORACLE_STEPS
from .runtime import WorkBudget

MAX_CANDIDATES = 4


@dataclass(frozen=True)
class CandidateRun:
    id: str
    static_rank: int
    behavior: BehaviorResult


@dataclass(frozen=True)
class Comparison:
    original: BehaviorResult | None
    candidates: tuple[CandidateRun, ...]
    passing: tuple[str, ...]
    review_order: tuple[str, ...]
    skipped_candidates: int
    status: str
    requires_approval: bool = True


def verify_repairs(result: IntentionResult, limits: ExecutionLimits, *, trace: bool = False) -> Comparison:
    """The caller owns the trust decision. This service has no HTTP integration."""
    requirement = result.context.requirement
    original_order = tuple(choice.id for choice in result.candidates)
    if result.finding == "UNSUPPORTED_LANGUAGE":
        return Comparison(None, (), (), original_order, len(original_order), "EXECUTION_UNSUPPORTED")
    if not requirement or not requirement.function or not 1 <= len(requirement.examples) <= 12:
        return Comparison(None, (), (), original_order, len(original_order), "ORACLE_UNAVAILABLE")
    result.behavior = None
    for choice in result.candidates:
        choice.behavior = None
    vectors = tuple(Vector(arguments=row.args, expected=row.expected_return) for row in requirement.examples)
    budget = WorkBudget(ORACLE_STEPS)
    oracle = MiniCOracle(trace=trace, budget=budget)
    original = oracle.verify(result.context.source, requirement.function, vectors, limits)
    if result.context.compiler_valid:
        result.record_behavior(original)
    runs = []
    for rank, choice in enumerate(result.candidates, 1):
        if len(runs) >= MAX_CANDIDATES or budget.remaining == 0:
            break
        if choice.compiler_valid:
            evidence = oracle.verify(choice.proposed_code, requirement.function, vectors, limits, candidate_id=choice.id)
            result.record_behavior(evidence)
            runs.append(CandidateRun(choice.id, rank, evidence))
    passing = tuple(row.id for row in runs if row.behavior.status == Status.MATCHES_SUPPLIED_TESTS)
    # Keep all passing candidates visible. Only move them forward after an observed failure,
    # and preserve the order within both partitions.
    outrank = original.status == Status.MISMATCHES_SUPPLIED_TESTS or (
        original.status == Status.BEHAVIOR_UNKNOWN and original.execution is not None
        and original.execution.issue is not None and original.execution.issue.code != "INTERNAL_FAILURE"
    )
    review_order = (*passing, *(key for key in original_order if key not in passing)) if outrank else original_order
    status = "MULTIPLE_MATCHES" if len(passing) > 1 else "ONE_MATCH" if passing else "NO_OBSERVED_MATCH"
    return Comparison(original, tuple(runs), passing, review_order, len(original_order) - len(runs), status)


def analyze_with_behavior(
    source: str, requirement: Requirement, limits: ExecutionLimits, *, trace: bool = False,
) -> tuple[IntentionResult, Comparison]:
    """Analyze explicit static requirements or use code-only hypotheses with test vectors."""
    static_requirement = requirement if (
        requirement.description or requirement.return_expression or requirement.condition
    ) else None
    result = analyze_intention(source, static_requirement, phase35=True)
    # Test vectors are a separate signal. They do not count as a static expression.
    result.context.requirement = requirement
    return result, verify_repairs(result, limits, trace=trace)
