# Independent external validation

| Fresh upstream defect | Original outcome | Isolated Phase 11 result |
| --- | --- | --- |
| Python exponential search below the first cell | Recursive endpoint reset reaches the depth limit | Unsupported. No candidate. |
| JavaScript empty numeric mean | Nonnumeric empty outcome normalized to division by zero | A guarded rejection passes discovery and holdout. The normalized source differs from the reference. |
| Java one-row matrix binary search | The physical end is passed as an inclusive index | Exact endpoint repair passes discovery and holdout. |

The three faults are documented upstream adaptations. Phase 11 matched the Phase 10.5 result on the same final cohort. Both successful mechanisms are inherited. Acceptable recovery was 2/3 with a Wilson 95% interval of 20.8%–93.9%. Exact recovery was 1/3 with a Wilson interval of 6.1%–79.2%. No independent human reviewer was available. [Pinned upstream replay](../benchmarks/reports/phase11-upstream-v1.json) · [Worker results](../benchmarks/reports/phase11-live-v1.json)
