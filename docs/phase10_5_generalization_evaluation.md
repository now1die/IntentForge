# Generalization and ablations

| Static configuration | Guided exact, documented | Guided exact, injected |
| --- | ---: | ---: |
| Phase 9, 9.5 or 10, each | 0/3 | 0/5 |
| Endpoint only | 0/3 | 1/5 |
| Adjacent only | 0/3 | 1/5 |
| Rotation only | 0/3 | 1/5 |
| Zero guard only | 0/3 | 1/5 |
| Aggregate only | 0/3 | 1/5 |
| Full Phase 10.5 with any one component disabled | 0/3 | 4/5 |
| Full Phase 10.5 | 0/3 | 5/5 |

Code-only exact repair was 0/8. Full Phase 10.5 yielded two endpoint candidates and one each for adjacent cells, rotation, guard and aggregate. In isolated evaluation one upstream repair was behaviorally acceptable and five injected repairs matched their source references. The earlier public profiles emitted no candidates on this cohort.

Of 133 semantics-preserving source rewrites, 131 preserved candidate-category and sampled-behavior signatures. An unused shadow scope removed the candidate in two endpoint cases. Those misses are recorded alongside the unchanged original observations and source checked on every emitted candidate.

Median guided analysis was 7.3 ms and p95 was 20.2 ms. Median isolated round trip including any holdout was 309 ms and p95 was 708 ms on the local host. The final worker used 30,455 discovery VM steps and 3,400 holdout steps. The maximum observed depth was five and peak occupancy was 56 cells. [Ablations and metamorphic replay](../benchmarks/reports/phase105-static-v1.json) · [Worker costs and intervals](../benchmarks/reports/phase105-live-v1.json)
