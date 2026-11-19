"""Exercise observation adjudication without running a user program."""

import pytest

from benchmarks.behavior import BehaviorSpec, BehaviorStatus, verify_behavior


SPEC = BehaviorSpec.from_dict({
    "entry": "twice",
    "tests": [{"args": [0], "expected_return": 0}, {"args": [3], "expected_return": 6}],
})
CORRECT = "int twice(int x){return x*2;}"
WRONG = "int twice(int x){return x+x+1;}"


class FixtureOracle:
    def observe(self, source, specification, *, timeout_seconds):
        assert timeout_seconds == .25 and specification is SPEC
        return {CORRECT: (0, 6), WRONG: (1, 7)}[source]


def check(source, spec=SPEC, **kwargs):
    return verify_behavior(source, spec, **({"compiler_valid": True, "supported": True, "timeout_seconds": .25} | kwargs))


def test_correct_and_wrong_compilable_sources_get_different_observations():
    match = check(CORRECT, oracle=FixtureOracle())
    mismatch = check(WRONG, oracle=FixtureOracle())
    assert (match.status, match.passed, match.observed) == (BehaviorStatus.VERIFIED, 2, 2)
    assert (mismatch.status, mismatch.passed, mismatch.observed) == (BehaviorStatus.MISMATCH, 0, 2)


def test_no_oracle_missing_spec_and_unsupported_feature_have_separate_states():
    assert check(CORRECT).status == BehaviorStatus.ORACLE_UNAVAILABLE
    assert check(CORRECT, None, oracle=FixtureOracle()).status == BehaviorStatus.UNVERIFIED
    assert check(None).status == BehaviorStatus.UNVERIFIED
    assert check("int f(int *x){return *x;}", supported=False).status == BehaviorStatus.EXECUTION_UNSUPPORTED


@pytest.mark.parametrize("error, clause", [(TimeoutError(), "timed out"), (ValueError(), "failed")])
def test_oracle_errors_do_not_count_as_behavioral_observations(error, clause):
    class BrokenOracle:
        def observe(self, *args, **kwargs):
            raise error
    result = check(CORRECT, oracle=BrokenOracle())
    assert result.status == BehaviorStatus.UNVERIFIED
    assert result.observed == 0 and result.specified == 2
    assert clause in result.reason
