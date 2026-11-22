# Candidate precision

The final worker saw two confirmed completed-output mismatches among six faults, three runtime failures and one execution limit. Confirmed precision was 2/2 and confirmed recall 2/6. No correct control produced a confirmed alert. One of nine controls produced three inherited speculative suggestions and the workbench kept all three collapsed.

Ten candidates compiled. Seven passed discovery and six passed fresh holdout. One of fifteen cases received a recommendation and fourteen did not. The single recommendation passed holdout. One fault case had multiple discovery-passing candidates. On the same candidate pool, static and behavioral exact top-1 and top-3 each measured 3/6. [Metrics with Wilson intervals](../benchmarks/reports/phase115-live-v1.json)
