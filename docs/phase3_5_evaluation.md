# Phase 3.5 consolidated evaluation

The final corpus contains 18 separated families and 14 accepted repair
references. Training and selection were frozen beforehand. All ranker
comparisons below use the same v4 candidate pool.

| Configuration | Top 1 | Top 3 | Candidate recall |
|---|---:|---:|---:|
| V3 baseline end to end | 3/14 | 4/14 | 4/14 |
| V4 deterministic and deployed | 6/14 | 7/14 | 7/14 |
| V2 or V3 on V4 candidates | 6/14 | 7/14 | 7/14 |
| V4 pointwise, pairwise or boosted, experimental | 7/14 | 7/14 | 7/14 |

V4 produced 21 compiler-valid proposals out of 27. Code-only alerts
had 4/10 recall and 4/4 precision on this labeled sample, with 0/3
alerts among confirmed valid controls. The abstention rule withheld
recommendation in 15/18, and every speculative repair required review.
Local code-only v4 mean runtime was approximately 3.6 ms and p95 was
10.2 ms, including generation and deterministic ordering. Experimental
orderings averaged 3.7–3.8 ms. These are descriptive local timings.

On the matched four-case requirement subset, top 1 was 0/4 code-only,
3/4 natural language, and 4/4 explicit. The fourth natural description
was unsupported and abstained. Both external adaptations were missed
code-only. No historical denominators or labels changed.

Clang verified 12 API scenarios, 13 AST units and six exact diagnostic
editor positions. Source spans, types, macros and separate language
routing were checked by fixtures. Security negative tests cover the
worker and transport, with production deployment unverified. Held-out
selective risk is documented separately. Live Ollama was unavailable.
Behavioral oracle tests use fixtures and carry no runtime correctness
claim.

```bash
python -m benchmarks.phase35_audit
python -m benchmarks.phase35_evaluate --check
python -m benchmarks.clang_analysis --check
python -m pytest -q tests/test_phase35_workstreams.py tests/test_clang_backend.py
```

[Machine-readable evaluation](../benchmarks/reports/phase35-evaluation-v1.json)
