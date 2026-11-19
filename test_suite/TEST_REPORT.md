# AI Compiler Test Run Report

- Total test cases executed: **220**
- Passed expected-behavior checks: **220**
- Mismatches needing review: **0**

## Actual outcomes

| Actual outcome | Cases |
|---|---:|
| ACCEPTED | 104 |
| LEXICAL_ERROR | 31 |
| SEMANTIC_ERROR | 43 |
| SYNTAX_ERROR | 42 |

## Coverage by test group

| Group | Cases | Matched expectations |
|---|---:|---:|
| Valid programs | 22 | 22 |
| Operators and expressions | 29 | 29 |
| Arrays functions and control flow | 28 | 28 |
| Lexical errors | 17 | 17 |
| Syntax errors and unsupported constructs | 42 | 42 |
| Semantic errors | 34 | 34 |
| Boundary and language edge cases | 28 | 28 |
| Lexer and parser regression fixes | 20 | 20 |

## Notable behavior observations

- `a.b;` is rejected at the lexical layer: `.` produces `ILLEGAL_CHARACTER`, followed by a parser diagnostic. Member access is not part of Mini-C.
- `sizeof(x)` is rejected semantically as `SEM-UNDECLARED-IDENTIFIER`; `sizeof` is not implemented as a keyword/operator in this subset.
- Array bounds checking is deferred in the project specification, so out-of-range access and negative integer array sizes can pass the current semantic phase.
- Incomplete numeric exponents such as `1e+` and `.5e-` are now caught by the lexer as `MALFORMED_NUMBER` rather than being split into unrelated parser tokens.
- Floating-point literals that overflow to infinity now produce `NUMERIC_LITERAL_OUT_OF_RANGE` lexical diagnostics.
- Unknown/incomplete character and string escapes now produce lexical diagnostics. Simple, octal, and hexadecimal escapes remain accepted; Unicode escapes are supported in strings.

## Mismatches

No mismatches between the test expectations and actual project behavior.

## Interpretation

`ACCEPTED` means lexical analysis, parsing, and semantic analysis all completed without diagnostics. `LEXICAL_ERROR`, `SYNTAX_ERROR`, and `SEMANTIC_ERROR` identify the earliest failing phase. `REJECTED` is used for unsupported syntax where a lexical or parser rejection is acceptable. This test set is broad representative coverage, not a mathematical enumeration of every possible source program.

## Artifacts

- `test_results.csv`: full table with source input, expected and actual outcomes, counts, diagnostic codes and messages.
- `test_cases_and_results.json`: machine-readable version of all tests and results.
- `test_cases.mc`: compact source corpus with case labels as comments.
