# False positives and counter-evidence

| Phase 5 heuristic | Phase 5.5 intervention | Remaining risk |
| --- | --- | --- |
| Loop progress binding | Withhold after a provable direct exit before update, a dead branch or a later use of the separately updated binding. | Conditional progress and side effects can remain ambiguous. |
| Fixed array edge | Withhold when a literal Boolean branch or a direct unconditional block transfer excludes the access. | General reachability and symbolic bounds remain outside the gate. An inherited Phase 3.5 candidate can still appear. |
| Argument role permutation | Withhold across separate call contexts, for a simple commutative callee or when the arguments may change. | Even equal-weight calls can deliberately use different orientations. Earlier heuristics can still alert on a valid program. |
| Accumulator consistency | Withhold code-only sign changes based solely on majority vote. | A genuine wrong-sign edit can be missed until a specification supplies the intended signs. |

The earlier Phase 5 false alerts include deliberate reversal and mixed-sign arithmetic. The new controls include distinct counters, a nested shadowed counter, an unreachable array access, different lexical arrays, valid direction branches and signed reconciliation. Dedicated tests check known positives, missing evidence, and counter-evidence for each family.

On admitted development controls, loop gating reduced end-to-end false alerts from 3/3 to 2/3. Array and argument gates withheld the Phase 5 hypotheses, while older candidate paths still raised their alerts. In the frozen final cohort, the loop gate removed one false alert. Accumulator abstention also removed a valid reference from the pool. Both outcomes remain in the results.

```sh
python -m pytest -q tests/test_phase55.py
python -m benchmarks.phase55_evaluate --check
```
