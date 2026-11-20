# Phase 6 isolated behavioral verification

The gateway reuses the existing Linux worker and typed test contracts. Test-guided generation includes one additional exact singleton base-case repair on the final cohort. For the same test-guided candidate pool, static and observed top-1 and top-3 were each 6/16. Code-only recall was 5/16. The test-guided pool is a separate condition.

The 34 original runs produced 17 matches, 12 mismatches, 3 execution limits, one program fault and one compiler-invalid admission. Worker issue codes separated call-depth and step limits from an uninitialized read. Nine candidate runs matched and four mismatched. One final case had multiple matches. Eight probes separated three pairs at 273 VM steps, while test execution consumed 20,702 steps. The gateway median was 396 ms and p95 was 751 ms in the recorded local run.

The real worker stopped a recursive original at `CALL_DEPTH` for input 4, which had a supplied expectation of 8. The one-site recursive progress candidate returned observed 8. The workbench displays the supplied vector, runtime status and candidate diff, and leaves approval to the user.

Controlled private fixtures supplied at the trusted worker boundary separated differing recursive guard thresholds with input 3 and distinguished a recursive limit at input 2. The equivalent return pair remained unresolved. Existing boundary and signed scalar probe generation supported these cases without changing the worker protocol or budgets. Generated observations carry no expected outputs.

```sh
python -m benchmarks.phase6_evaluate --live --check
```

[Machine-readable live results](../benchmarks/reports/phase6-live-v1.json) · [Worker profile](phase4_5_execution_isolation.md)
