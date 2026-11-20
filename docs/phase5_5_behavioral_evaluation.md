# Behavioral review and ambiguity

| Evaluation mode | Observed result |
| --- | --- |
| Code-only static | 2/19 exact references, all at position one. |
| Natural-language guidance | 0/19 exact references for the provided task descriptions. |
| Explicit specifications | 2/2 exact references for the supplied expression and selector subset. |
| Behavior with trusted expectations | Top-1 remained 2/19. Five candidates matched and two mismatched their supplied tests. |
| Observation only | The partial-specification requests retained static order and separated one candidate pair without supplying expected values. |

Across 40 isolated original executions, 20 matched, 17 mismatched, one had a runtime fault, one hit an execution limit and one was unsupported by the oracle. One case had multiple passing alternatives. Eight generated probes separated one pair at a cost of 170 VM steps. Seven probes added no previously unseparated pair. The local gateway round-trip median was 652 ms and the p95 was 1.67 s under shared test load.

The controlled same-pool fixtures preserve two passing alternatives before probing. The equivalent add-zero pair remained equivalent after 72 steps. The boundary-fault pair separated at 117 steps, and the partial-specification pair separated at 60 steps. These fixtures were submitted by the benchmark through the private owner-only transport. Public callers still receive only server-generated alternatives. Candidate outcomes never supply the expected return for a new test vector.

```sh
python -m benchmarks.phase55_evaluate --live --check
```

[Live report](../benchmarks/reports/phase55-live-v1.json) · [Local worker setup](phase4_5_execution_isolation.md)
