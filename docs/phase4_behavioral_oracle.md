# Interpreter-backed behavioral oracle

`vm.behavioral_executor.MiniCOracle` implements the existing
`BehaviorOracle.verify` protocol. The selected entry point must return
int or bool. Every argument and expected return is checked against its
exact type, arity and numeric range before any test executes. An empty
vector set produces `ORACLE_UNAVAILABLE`.

When execution completes, the result includes actual scalar outputs.
`MATCHES_SUPPLIED_TESTS` requires a matching observation for every
supplied vector. `MISMATCHES_SUPPLIED_TESTS` requires completed
execution and an observed counterexample. Limits and runtime failures
keep their separate statuses and may include earlier observations.
Compiler validity is tracked independently.

The version 1 schema retains its existing fields and statuses.
Optional `execution` adds provider, supplied vectors, per-vector
step and storage samples, a structured failure and trace. Integration
checks the SHA-256 of the source, entry point, candidate ID and exact
typed vectors. Both the original program and every executed candidate
receive their own identity. The trusted caller owns the execution
decision. No HTTP route attaches these results.

```python
from ai.behavior_oracle import ExecutionLimits, Vector
from vm.behavioral_executor import MiniCOracle

result = MiniCOracle(trace=True).verify(
    "int twice(int x){return x*2;}",
    "twice",
    (Vector(arguments=(4,), expected=8),),
    ExecutionLimits(),
)
print(result.model_dump_json(indent=2))
```
