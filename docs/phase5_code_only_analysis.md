# Binding-aware code-only analysis

The scan indexes AST subtree ranges, resolved lexical bindings and direct assignment/update sites. It checks whether the body writes the initialized loop binding, whether a constant index equals the length of the visible array, whether direct calls with the same bindings use inconsistent parameter ordering, and whether adjacent updates to one accumulator differ in sign. Scope identity is used even when two declarations share a name.

The scan requires a compiler-valid AST. It reports incomplete compiler evidence or a bounded scan when appropriate. A local dependency is not a whole-program invariant. Aliasing, indirect calls, interprocedural effects, control-flow joins and full specifications remain outside this analysis. Legitimate mixed signs and deliberately reversed argument roles can trigger hypotheses. The final cohort measures those false alerts.

```sh
python -m pytest -q tests/test_phase5_static.py
python -m benchmarks.phase5_evaluate --check
```
