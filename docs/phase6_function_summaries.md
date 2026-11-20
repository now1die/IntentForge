# Function summaries

The Phase 6 response describes parameters, return type, direct calls, direct and bounded mutual recursion, normalized atomic conditions, known reaching return definitions, direct and possible writes, and graph completeness. Nonvoid paths that can reach exit without a return are flagged as possible missing returns.

Call edges come from reachable graph blocks. Bounded cycle search identifies direct and mutual recursion. Calls carry possible global effects because the engine does not compute interprocedural value summaries. Function flags identify merged arrays, approximate call effects and types outside the proven VM subset. Missing-return evidence uses the graph and can include infeasible nonliteral paths.

```sh
python -m pytest -q tests/test_phase6.py -k 'unknown_global or cfg'
```
