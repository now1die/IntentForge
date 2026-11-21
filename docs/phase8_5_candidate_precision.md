# Candidate precision and review burden

On the final cohort, Phase 8.5 confirmed original mismatches for 13/14 faults
and raised 0/14 confirmed control alerts. Its recommendations covered 9/30
cases. Twenty-one cases had no recommendation and two cases had multiple
discovery-passing alternatives.

The worker admitted 13 candidates. All passed discovery and 12 passed
holdout. The failed relay-grid alternative incorrectly accepted `[0,2]` and
`[1,2]`. The gateway had withheld a recommendation because multiple
candidates fit discovery. All nine recommended alternatives passed holdout.
The finite relay domain was checked on all nine specified points across the
two partitions, and one candidate passed both.

On the new controls the default view showed zero suggestions. In a same-pool
presentation comparison on seven archived controls, 17 optional suggestions
remained accessible and zero appeared initially. The evaluation confirms that
Phase 8 and 8.5 returned the same candidate IDs on those archived controls.

The worker presented the same exact top-1 and top-3 results as the static
order on the isolated candidate pool. That pool yielded 9/14 and 10/14.
Behavioral verification provided evidence for review even when it left ranks
unchanged.
[Isolated measurements](../benchmarks/reports/phase85-live-v1.json)
