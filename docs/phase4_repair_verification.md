# Behavioral comparison of repairs

Call `vm.repair_verification.analyze_with_behavior` on trusted source
and a requirement with the chosen entry function and test examples.
The existing static engine generates and validates the candidates.
Example-only verification preserves code-only hypotheses. Natural
language or explicit expressions continue contributing static evidence
as before.

The original program is evaluated separately. A compiler-invalid
original reports unavailable execution with a compiler diagnostic.
The comparison runs up to four compiler-valid alternatives under the
same vectors and shared budget, and counts skipped candidates. It
attaches behavior only through the existing snapshot checks.

Static ordering and scores remain intact. A separate review order
moves test-passing alternatives ahead only when the original had an
observed output mismatch or a program runtime fault. This order
retains static order within each group. Multiple passing alternatives
are visible and marked ambiguous. Passing a supplied test set never
automatically applies a repair or proves intended behavior.

```bash
python -m pytest -q tests/test_phase4_vm.py tests/test_phase35_workstreams.py
python -m benchmarks.phase4_vm --check
```
