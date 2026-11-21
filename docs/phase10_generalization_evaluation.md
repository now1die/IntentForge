# Generalization evaluation

Code-only exact recovery was 0/9 across profiles. On the frozen final cohort, Phase 8.5, 9 and 9.5 found no discovery-passing candidate. Phase 10 had five exact guided repairs among five injected defects, with a Wilson 95% interval of 56.6%–100%. The upstream source-reference rate remained 0/4. Isolated testing verified one additional behaviorally acceptable upstream repair.

| Static ablation on identical final inputs | Injected exact | Documented exact |
| --- | ---: | ---: |
| Phase 8.5, 9 or 9.5, each | 0/5 | 0/4 |
| Fixed index only | 1/5 | 0/4 |
| Search interval only | 1/5 | 0/4 |
| Expansion only | 1/5 | 0/4 |
| Range origin only | 1/5 | 0/4 |
| Helper progress only | 1/5 | 0/4 |
| Any one component disabled | 4/5 | 0/4 |
| Full Phase 10 | 5/5 | 0/4 |

Discovery produced two search candidates and one each for fixed index, handoff, derived range and helper progress. The 131 semantics-preserving rewrites yielded zero sampled candidate-category or behavior differences. The evaluator also verifies each rewritten candidate's source offsets and approval requirement.

Median guided projection was 6.3 ms and p95 was 15.7 ms locally. Median isolated round trip including any holdout replays was 291 ms and p95 was 636 ms. The final worker runs observed 17,800 discovery VM steps and 2,241 holdout steps, with a peak of 408 cells and maximum call depth 32. These timings depend on the host.

The small benchmark tests numeric subsets and bounded transitions. It provides a first estimate of recovery on these families. [Ablations and metamorphic results](../benchmarks/reports/phase10-static-v1.json) · [Isolated results](../benchmarks/reports/phase10-live-v1.json)
