# AI Compiler Test Suite

This suite contains 220 representative Mini-C programs/snippets designed to exercise the compiler that is in the parent project directory. It covers ordinary programs, scalar types, literals, arithmetic and logical operators, precedence, arrays, functions, parameters, scopes, if/else, while/for, loop control, lexical errors, syntax errors, unsupported C constructs, semantic/type errors, and boundary cases.

## Run it

From the project root (`ai compiler/`), after installing the project's requirements:

```bash
python test_suite/run_test_cases.py
```

The runner uses the project's real `analyze_source_semantics()` pipeline. It checks each source string and regenerates:

- `test_results.csv` — opens in Excel; includes test ID, category, test code, expected result, actual result, diagnostic codes/messages and PASS/FAIL.
- `test_cases_and_results.json` — machine-readable test data and actual output.
- `test_cases.mc` — a compact labelled corpus for browsing/copying inputs.
- `TEST_REPORT.md` — totals, outcome counts, coverage by group, notable behavior and any mismatches.

The suite is broad representative coverage, not every syntactically possible program. A `REJECTED` expected outcome allows a documented unsupported construct to be rejected at the lexical, syntax, or semantic phase; its actual phase is still recorded.

## Current verification

The most recent run matched all **220/220** expected outcomes. Regression cases now check malformed exponents (`1e+`, `.5e-`), exponent overflow, valid exponent controls, unsupported escapes, valid escape decoding, consecutive operators, comments adjacent to operators, and unsupported member access (`a.b;`).

A larger 3,758-case stress suite is available in `test_suite/stress/`. It records exploratory operator combinations separately from labelled pass/fail expectations.
