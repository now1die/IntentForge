# AI Compiler Stress Tests

This directory contains the generated 3,758-case lexer/parser/semantic stress suite and the results from the fixed compiler.

Run from the project root after installing `requirements.txt`:

```bash
python test_suite/stress/run_stress_tests.py .
```

The test generator includes malformed numeric literals, string/character escape cases, operator-pair and operator-triple probes, comment boundaries, syntax mutations, semantic errors, and deep nesting/truncation cases. Exploratory cases are recorded as `OBSERVED`; they do not assume every operator pairing must pass or fail.

Generated files:
- `AI_Compiler_Stress_Results.csv` — all cases and observed diagnostics.
- `AI_Compiler_Stress_Results.json` — machine-readable results.
- `AI_Compiler_Stress_Report.md` — summary and review findings.
- `AI_Compiler_Rejected_Cases.csv` — all rejected programs with their first diagnostic phase.
