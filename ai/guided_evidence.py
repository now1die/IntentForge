"""Phase 7 classification of verified evidence, independent of synthesis."""
from enum import StrEnum

from ai.behavior_oracle import BehaviorResult, Status


class OriginalEvidence(StrEnum):
    CONFIRMED_TEST_MISMATCH = "CONFIRMED_TEST_MISMATCH"
    ORIGINAL_MATCHES_SUPPLIED_TESTS = "ORIGINAL_MATCHES_SUPPLIED_TESTS"
    INSUFFICIENT_SPECIFICATION = "INSUFFICIENT_SPECIFICATION"
    RUNTIME_FAILURE = "RUNTIME_FAILURE"
    EXECUTION_LIMITED = "EXECUTION_LIMITED"
    EXECUTION_UNSUPPORTED = "EXECUTION_UNSUPPORTED"
    VERIFICATION_UNAVAILABLE = "VERIFICATION_UNAVAILABLE"


class ReviewEvidence(StrEnum):
    REVIEW_MATCHING_REPAIR = "REVIEW_MATCHING_REPAIR"
    MULTIPLE_PLAUSIBLE_REPAIRS = "MULTIPLE_PLAUSIBLE_REPAIRS"
    POSSIBLE_REPAIR = "POSSIBLE_REPAIR"
    ABSTAIN = "ABSTAIN"


ORIGINAL_STATUS = {
    Status.MATCHES_SUPPLIED_TESTS: OriginalEvidence.ORIGINAL_MATCHES_SUPPLIED_TESTS,
    Status.MISMATCHES_SUPPLIED_TESTS: OriginalEvidence.CONFIRMED_TEST_MISMATCH,
    Status.EXECUTION_LIMITED: OriginalEvidence.EXECUTION_LIMITED,
    Status.EXECUTION_UNSUPPORTED: OriginalEvidence.EXECUTION_UNSUPPORTED,
    Status.ORACLE_UNAVAILABLE: OriginalEvidence.INSUFFICIENT_SPECIFICATION,
}


def classify_original(original: BehaviorResult | None) -> OriginalEvidence:
    if original is None:
        return OriginalEvidence.VERIFICATION_UNAVAILABLE
    if original.status == Status.BEHAVIOR_UNKNOWN:
        issue = original.execution.issue if original.execution else None
        return (OriginalEvidence.RUNTIME_FAILURE if issue and issue.code != "INTERNAL_FAILURE"
                else OriginalEvidence.VERIFICATION_UNAVAILABLE)
    return ORIGINAL_STATUS[original.status]


def classify_review(original: OriginalEvidence, candidates: int, matches: int) -> ReviewEvidence:
    if original == OriginalEvidence.CONFIRMED_TEST_MISMATCH and matches == 1:
        return ReviewEvidence.REVIEW_MATCHING_REPAIR
    if matches > 1:
        return ReviewEvidence.MULTIPLE_PLAUSIBLE_REPAIRS
    return ReviewEvidence.POSSIBLE_REPAIR if candidates else ReviewEvidence.ABSTAIN


def comparable_outcome(item):
    if item.status == "observed":
        return ("value", type(item.actual), item.actual)
    if item.status in {"runtime_failure", "execution_limited"} and item.issue != "VERIFICATION_BUDGET":
        return (item.status, item.issue)
    return None



def conflicting_expectations(rows):
    observed = {}
    for arguments, expected in rows:
        key = tuple((type(value), value) for value in arguments)
        outcome = (type(expected), expected)
        if observed.setdefault(key, outcome) != outcome:
            return True
    return False
