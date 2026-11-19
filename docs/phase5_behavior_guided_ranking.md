# Behavior-guided ranking

A version 5 POST to `/v1/behavioral-verification` accepts the Phase 4.5 contract and `engine_version: 5`. An empty vector list is accepted only with candidate comparison enabled. This mode preserves static rank and returns observational probes without test-match statuses.

With explicit test vectors, the response holds original behavior, candidate behavior, static rank, behavioral review order and a multiple-match status. For a witnessed original mismatch, a recognized original fault or a candidate-relevant admission failure, the separate review order places observed matches first and mismatches next. Candidates in each tier retain their static order. If the original already matches, static order is retained. Passing examples support review within those examples. Multiple passing alternatives remain separate.

Version 5 deploys the existing deterministic ordering. The published v4 gated and pairwise artifacts and the experimental structural-feature ordering are compared on identical candidate IDs. Neither same-pool experiment improved the selection comparison. The small selection set provided no candidates eligible for learned scoring. The experimental pairwise artifact scored five final candidates without improving top-1 or top-3. No new model was fitted, and the original v1–v4 paths remain available.

```sh
python -m pytest -q tests/test_phase5_behavior.py
python -m benchmarks.phase5_evaluate --live --check
```

[Restricted local setup](phase4_5_execution_isolation.md)
