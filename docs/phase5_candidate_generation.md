# Bounded candidate generation

| New family | Required evidence | Edit |
| --- | --- | --- |
| Loop progress binding | A unit update and an ordered loop guard refer to different bindings, and the body does not update the guard binding. | Redirect the update to the guarded index. |
| Fixed array edge | A literal index equals the length of its visible fixed-size array. | Use the highest valid index as an alternative. |
| Argument permutation | At least two direct peer calls agree on the order of the same identifiers and one reverses two roles. | Swap two identifier spans. |
| Accumulator consistency | Adjacent updates to one integer binding have distinct parameter inputs and a dominant sign. | Change at most two minority updates together. |

The bounded scan considers at most 1,200 nodes and emits at most six hypotheses. It shares the existing intention-analysis deadline and 24-validation ceiling. The existing engine checks distinct, non-overlapping edits, source and structural duplicates, remaining compiler diagnostics and validated candidates. Each candidate carries a stable identity, a location-preserving edit list, compiler evidence, the assumption and an explicit review requirement.

Arithmetic, comparisons, loop conditions and initializers, return edits and missing bindings already have scoped proposal paths. Generalized arbitrary expressions, multi-function edits and unrestricted token substitution remain outside this implementation.

```sh
python -m pytest -q tests/test_phase5_static.py
python -m benchmarks.phase5_evaluate --check
```
