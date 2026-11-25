# Phase 12 baseline

Phase 12 starts at `24c8d09463e5b86dd4f4b19252203123b3dfec16`, the fetched head of `phase-1-intention-benchmarking` and merge of [PR #22](https://github.com/now1die/IntentForge/pull/22).

All post-merge runs completed successfully.

| Workflow | Run |
| --- | --- |
| Python | [45046975624](https://github.com/now1die/IntentForge/actions/runs/45046975624) |
| Clang | [45046975490](https://github.com/now1die/IntentForge/actions/runs/45046975490) |
| Frontend | [45046975409](https://github.com/now1die/IntentForge/actions/runs/45046975409) |
| Benchmarks | [45046975445](https://github.com/now1die/IntentForge/actions/runs/45046975445) |
| Isolated Mini-C | [45046975426](https://github.com/now1die/IntentForge/actions/runs/45046975426) |

The frozen Phase 11.5 holdout recovered 0/3 documented faults, 3/3 injected faults and 2/4 archived faults behaviorally. Exact counts were 0/3, 3/3 and 1/4 respectively. Ten candidates compiled, seven passed discovery and six passed holdout. There were zero confirmed alerts among nine correct controls. One correct control had three collapsed speculative alternatives. All 131 measured transformations preserved signatures. [Baseline report](../benchmarks/reports/phase115-live-v1.json)

Local offline benchmark checks from the review corpus through Phase 11.5 and the compiler, keyboard-array, and stress runners were replayed on the verified worktree before final verification. Phase 11.5 candidate and report files remain pinned.
