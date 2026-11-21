# Generalization evaluation

Run `python -m benchmarks.phase75_evaluate --check` and add `--live` with the verified local worker. The versioned reports include case outcomes, Wilson intervals, static and worker timing, independent holdout results and per-condition metrics.

| Generator | Code-only exact | Guided exact | Guided hypotheses on controls |
| --- | ---: | ---: | ---: |
| Phase 6 | 1/24 | 1/24 | 0/24 |
| Phase 6.5 | 0/24 | 1/24 | 0/24 |
| Phase 7 | 0/24 | 1/24 | 0/24 |
| Phase 7.5 helper layout only | 0/24 | 1/24 | 0/24 |
| Phase 7.5 nonunit only | 0/24 | 4/24 | 2/24 |
| Phase 7.5 dependencies only | 1/24 | 9/24 | 3/24 |
| Phase 7.5 combined | 1/24 | 16/24 | 7/24 |

Phase 7 and 7.5 both confirmed 23/24 faults and 0/24 control alerts on the same supplied vectors. Phase 7.5 recovered 4/6 new external faults with exact edits that passed both suites. Test-guided exact recall was 12/18 on internally authored fault families. The separate natural-language and explicit-specification slices each contained one fault and produced no exact repair. Observation-only requests executed for all seven partially specified cases.

The same Phase 7.5 guided candidate pool moved exact top-1 from 8/24 static to 15/24 behavioral. Top-3 remained 16/24. Static ordering stays deterministic. The wider guided pool increases review load on correct controls, while the verified-original gate preserves the distinction between hypotheses and confirmed faults.
