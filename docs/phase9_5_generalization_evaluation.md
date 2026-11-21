# Generalization and ablations

Each configuration used the same 33 independently selected final records.
Every configuration had zero exact code-only repairs across the 15 faults.

| Static configuration | Exact guided repairs |
| --- | ---: |
| Phase 8.5 | 0/15 |
| Phase 9 | 2/15 |
| Phase 9 plus domain guards | 4/15 |
| Phase 9 plus window boundaries | 4/15 |
| Phase 9 plus range origins | 3/15 |
| Phase 9.5 without helper projection | 7/15 |
| Combined Phase 9.5 | 9/15 |

The combined profile emitted ten new proposals, comprising five window, three
domain and two range candidates. It retained two inherited candidates.
The 219 sampled source transformations preserved candidate categories and
observed effects. The profile defeated one of five held-out upstream defects
and eight of ten injected faults. Eight records fell outside the new
projection budget or grammar, three of them faulty.

The isolated worker used 20,434 discovery steps, 572 probe steps and 3,340
holdout steps. Peak sampled cells were 68 and peak call depth was five on the
original and candidate pool. The isolated comparison median was about 339 ms,
including follow-up holdout requests where applicable.
[Static report](../benchmarks/reports/phase95-static-v1.json) ·
[Isolated report](../benchmarks/reports/phase95-live-v1.json)

```bash
python -m benchmarks.phase95_audit
python -m benchmarks.phase95_upstream
python -m benchmarks.phase95_evaluate --check
python -m benchmarks.phase95_evaluate --live --check
```

The provenance replay needs Node and javac, or a Java runtime plus the path
to an Eclipse compiler JAR in PHASE95_ECJ_JAR. The isolated evaluation needs
the repository's restricted worker.
