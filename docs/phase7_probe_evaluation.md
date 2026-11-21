# Probe evaluation

Engine 7 retains the eight-input cap and shared 200,000-step budget. It mixes candidate-derived guard thresholds with supplied argument seeds and samples additional nearby values to expose later recurrence differences. Ranking favors new pair coverage, observable differences and cheaper probes. Inputs carry no expected outputs.

| Controlled pair | Phase 6.5 separated | Phase 7 separated | Phase 7 distinguishing input |
| --- | ---: | ---: | --- |
| Lagged recurrence | 0 | 1 | `[3]` |
| Joint branch and value argument | 0 | 1 | `[3, 4]` |
| Equivalent return expression | 0 | 0 | None |
| Runtime difference | 1 | 1 | `[3]` |

The same four controlled pairs cost 1,390 steps under the earlier generator and 1,826 under Phase 7. On the final cohort, the Phase 6.5 pool generated 12 probes and separated no additional pairs. Engine 7 generated 24 probes across its expanded pool, separated two of four available pairs, and spent 4,060 probe steps. Two pairs agreed on comparable probes. An agreement label only describes tested inputs.
