# Generalization and ablations

| Static configuration | Guided exact, documented | Guided exact, injected |
| --- | ---: | ---: |
| Phase 10, 10.5 or 11, each | 0/3 | 0/3 |
| Endpoint only | 0/3 | 1/3 |
| Cyclic only | 0/3 | 1/3 |
| Range only | 0/3 | 1/3 |
| Interpolation comparison only | 0/3 | 0/3 |
| Full Phase 11.5 | 0/3 | 3/3 |

Disabling any of endpoint, cyclic, or range reduced the injected exact count to two. The interpolation component adds comparison evidence without manufacturing an extra patch. Code-only exact recovery was 0/6. The worker confirmed all three injected repairs and none of the documented repairs. The exact top-1 and top-3 counts were 3/6 before and after behavioral ranking on identical candidate IDs.

All 131 final metamorphic transformations retained their sampled candidate signatures, and both archived shadow fixes were preserved. Median static analysis was about 15 ms locally, with p95 about 47 ms. Median isolated round trip including holdout was about 352 ms and p95 was about 1.24 seconds. Worker totals were 29,473 discovery steps and 4,801 holdout steps, with maximum call depth 32 and peak occupancy 408 cells. [Ablations](../benchmarks/reports/phase115-static-v1.json) · [Worker measurements](../benchmarks/reports/phase115-live-v1.json)
