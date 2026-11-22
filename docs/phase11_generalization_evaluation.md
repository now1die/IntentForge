# Generalization and component ablations

| Static configuration | Guided exact, documented | Guided exact, injected |
| --- | ---: | ---: |
| Phase 9.5 | 0/3 | 0/4 |
| Phase 10 or 10.5, each | 1/3 | 0/4 |
| Relational model only | 1/3 | 0/4 |
| Interpolation only | 1/3 | 0/4 |
| Helper contract only | 1/3 | 1/4 |
| Cyclic array only | 1/3 | 1/4 |
| Coordinated range only | 1/3 | 1/4 |
| Full Phase 11 | 1/3 | 3/4 |

Code-only exact repair was 0/7. The full pool contained seven candidates. Five came from the new categories, with two interpolation candidates and one each for helper contract, cyclic tie and range. The other two came from inherited profiles. Isolated verification matched the inherited gains on fresh upstream cases and accepted a repair for each injected fault. Both interpolation edits passed behaviorally and differed from the fixed source. Removing the cyclic, helper or range component removed its corresponding exact injected result. Removing interpolation did not change exact counts.

All 151 transformations preserved the category and sampled behavior signature on the final cases. The report includes the recovered archived shadow patterns independently. Median guided analysis was 13 ms and p95 was 43 ms. Median isolated round trip with holdout was 321 ms and p95 was 1,220 ms. The final worker recorded 25,453 discovery steps and 4,507 holdout steps, with peak occupancy of 479 cells and depth 32 across all final responses. [Ablations and transformations](../benchmarks/reports/phase11-static-v1.json) · [Worker metrics](../benchmarks/reports/phase11-live-v1.json)
