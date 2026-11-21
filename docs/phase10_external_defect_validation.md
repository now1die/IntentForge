# Independent documented defects

| Upstream fault | Phase 10 result | Original worker evidence |
| --- | --- | --- |
| Python recursive search empty interval | Entry guard passes holdout | Call-depth limit |
| Python zero LCM | No compatible proposal | Division by zero |
| Java duplicate lower bound | Unsupported interval contract | Confirmed output mismatch |
| Java short rotated-array pivot | Unsupported adjacent-cell search | Array bounds failure |

Across the four external cases, discovery and independent holdout accepted 1/4 repairs, with a Wilson 95% interval of 4.6%–69.9%. Exact source-reference recovery was 0/4. The passing recursive repair inserts the same guard before the local cell initialization, while the frozen reference places the guard after initialization. This difference leaves the sampled output unchanged and receives behavioral credit only.

The four cases are adapted documented upstream faults. The cohort has no native documented Mini-C defects, external repair-example cases or externally sourced programs with injected faults. Five internal injected faults are scored in their own group. No external human reviewer was available. [Raw replay](../benchmarks/reports/phase10-upstream-v1.json) · [Isolated results](../benchmarks/reports/phase10-live-v1.json)
