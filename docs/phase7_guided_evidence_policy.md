# Guided evidence policy

The original must complete all supplied test vectors and disagree on at least one observed value to produce a confirmed fault. An original that matches all supplied expectations receives its own agreement status. Limits, runtime faults, unsupported execution, unavailable verification and observation-only mode receive separate statuses. Contradictory expected outputs for the same typed input are rejected in engine 7.

When the original mismatches and exactly one alternative passes every vector, that candidate is eligible for guided review. Multiple passing alternatives are shown together for further specification. Other compiler-valid alternatives remain visible as possible repairs. A resource stop can leave a valuable repair available without promoting it as a verified semantic correction. Applying any candidate requires explicit approval.

The policy affects alerts and promotion independently of the static candidate pool. Agreement is scoped to tested inputs. Ranking within evidence groups is deterministic.
