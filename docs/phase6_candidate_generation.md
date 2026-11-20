# Bounded semantic synthesis

Three recursion categories and one terminal-return category have actual edit generators. The generators use compiler types, binding identities, reachable function structure and reaching definitions. They emit no more than six new hypotheses inside the shared 24-attempt budget. A new proposal has one or two source edits. Prior profile candidates remain available when compiler validation succeeds.

The existing validator rejects overlapping edits, compiler-invalid output and duplicate structural candidates. The new response includes the source fingerprint, candidate identity, analysis status, spans, assumptions, supporting and counter-evidence, proposed source, compiler outcome and explicit approval requirement. Deterministic ordering remains active. v4 and pairwise experiments use exactly the same compiler-valid pool.

The synthesis scope excludes generalized arithmetic operator search, automatic recurrence inference, unbounded expressions and whole-function rewrites. Scope-wide or multi-function modifications were outside Phase 6.

```sh
python -m benchmarks.phase6_evaluate --check
```
