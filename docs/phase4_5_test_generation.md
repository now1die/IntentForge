# Candidate-disagreement inputs

The worker explores distinct scalar inputs from zero, small signed values, Boolean alternatives and nearby literal branch thresholds within the shared execution budget. It considers up to eight vectors for compatible candidate signatures of at most four parameters. It abstains when candidate signatures differ or programs have globals. Already supplied vectors are excluded.

The evidence records each candidate's observed value or execution status and labels each probe agreement, disagreement or inconclusive. Candidate-specific runtime failure can distinguish options. When two candidates pass the supplied vectors, both remain marked as matches even if a generated probe distinguishes them. Copying a probe to the test input leaves its expected result empty until the reviewer supplies it.

```sh
python -m pytest -q tests/test_phase45_isolation.py
python -m benchmarks.phase45_isolation
```

See the [local profile](phase4_5_execution_isolation.md) for the live benchmark setup and the [recorded benchmark](../benchmarks/reports/phase45-isolation-v1.json) for results.
