# Generalization evaluation

Run `python -m benchmarks.phase8_evaluate --check` for the deterministic static, audit and metamorphic results. Use `--live --check` with the documented restricted worker for discovery, separate holdout, review presentation and behavioral ordering. The versioned reports include case-level results, Wilson intervals, checked domains, elapsed time and resource costs.

| Generator | Code-only exact | Guided exact | Guided hypotheses on correct controls |
| --- | ---: | ---: | ---: |
| Phase 6.5 | 0/23 | 0/23 | 0/23 |
| Phase 7 | 0/23 | 0/23 | 0/23 |
| Phase 7.5 | 0/23 | 0/23 | 0/23 |
| Phase 8 specification only | 0/23 | 0/23 | 0/23 |
| Phase 8 arithmetic only | 0/23 | 14/23 | 0/23 |
| Phase 8 dependencies only | 0/23 | 2/23 | 0/23 |
| Phase 8 full | 0/23 | 19/23 | 0/23 |

All 19 exact candidates passed holdout, including eight of eight admitted externally adapted faults. The cohort emphasizes scalar arithmetic and has limited coverage of real faults and unsupported control flow. Archived diagnostics recovered three of four selected misses. The coprime-count case remains unresolved. The separately evaluated explicit slice recovered 1/1 fault. The natural-language family was quarantined. Observation-only requests ran on six partial specifications.

On the same Phase 8 pool, static and behavioral exact top-1 were both 17/23 and top-3 were both 19/23. Deterministic ranking remains selected. All 234 VM-checked guided metamorphic comparisons preserved the candidate categories. Live runs observed 22 original mismatches, 29 matches and one runtime fault. They spent 4,523 discovery steps, 656 probe steps and 778 holdout steps. Sixteen probes separated two pairs. Reported latency includes the additional holdout request cost for passing candidates.
