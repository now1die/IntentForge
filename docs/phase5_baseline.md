# Phase 5 baseline

GitHub PR #8 merged Phase 4.5 at `b325a154707e20ca23e5a243b84a3318ca9b3d72` on `phase-1-intention-benchmarking`. The Phase 5 branch starts at that revision. The baseline Python run passed 650 tests with Clang enabled. The live Mini-C test is gated by the verified local socket. The Phase 4.5 delivery records the live service results separately.

Existing entry points are Mini-C static analysis and correction, versioned intention analysis with v2–v4 ranking, the restricted local Mini-C behavior gateway and Clang analysis. The Mini-C language and deployment limits are documented in the [Phase 4.5 review](PHASE_4_5_FINAL_REVIEW.md). The historical [failure taxonomy](phase5_failure_taxonomy.md) is derived from committed reports. Each cohort retains its original labels and denominators.

The production frontend build passed, with 26 browser tests passing and the
three live-only Phase 4.5 scenarios skipped in this baseline profile. All
historical audits and checks reproduced, including 12 Clang 19 scenarios,
220 compiler cases, 65 keyboard and array cases with zero unexpected outcomes,
and execution of the 3,758-case stress suite.
