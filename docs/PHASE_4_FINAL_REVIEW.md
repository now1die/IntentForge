# Phase 4 final review

**Complete with limitations.** A deterministic interpreter now executes
the documented Mini-C subset for trusted callers. Public editor-source
execution remains unavailable. Runtime verification is independent of
compiler validity, candidate ranking and manual approval.

| Workstream | Verified outcome |
|---|---|
| A. Interpreter | Checked integer/Boolean AST execution, functions, recursion, arrays and scoped state. |
| B. Bounds | Separate step, call, cell, vector, comparison, source and trace limits. |
| C. Oracle | Actual outputs with identity, vector and runtime evidence checks. |
| D. Repair | Original/candidate comparison, separate review order and ambiguous passing alternatives. |
| E. Workbench | Recorded evidence with traces and source-snapshot invalidation. |
| F. Evaluation | Semantic, differential-reference, repair, runtime and historical compatibility checks. |

Phase 4 supports trusted int and bool entry points and internal void
helpers. Float, char, string, bare control-body declarations and full C
are outside the execution subset. The case results describe the
supplied vectors only. Production execution isolation remains unverified.

[Baseline](phase4_baseline.md) ·
[Architecture](phase4_architecture.md) ·
[Semantics](phase4_vm_semantics.md) ·
[Language coverage](phase4_supported_language.md) ·
[Limits](phase4_execution_limits.md) ·
[Security](phase4_security.md) ·
[Oracle](phase4_behavioral_oracle.md) ·
[Repair verification](phase4_repair_verification.md) ·
[Evaluation](phase4_evaluation.md) ·
[Workbench and screenshots](phase4_workbench.md)

The regression suite includes 56 dedicated VM tests, the compiler and
keyboard/array suites, ML and Clang checks, and workbench browser tests.
The Python and Clang counts include their respective opt-in fixture
configurations. Reproduce by setting the Clang environment documented
in [the Clang integration guide](phase3_clang_integration.md).

```bash
python -m pytest -q
python -m benchmarks.phase4_vm --check
python -m benchmarks.clang_analysis --check
python -m test_suite.run_test_cases
python -m test_suite.run_keyboard_and_array_regression --verify
python -m test_suite.stress.run_stress_tests .
npm --prefix frontend run build
npm --prefix frontend test
```
