# AI Compiler Stress-Test Report

- Project tested: `/tmp/ai_final/ai compiler`
- Total cases executed: **3758**
- Runtime: **2.4 seconds**

## Actual outcomes

- **SYNTAX_ERROR:** 1701
- **LEXICAL_ERROR:** 1253
- **SEMANTIC_ERROR:** 722
- **ACCEPTED:** 82

## Test harness outcome

- **OBSERVED:** 3498
- **PASS:** 255
- **REVIEW_REJECTED:** 3
- **REVIEW_ACCEPTED:** 2

## Unexpected outcomes

No expected-accept cases were rejected and no expected-reject case was accepted in the labeled cases. Exploratory operator probes are recorded as OBSERVED, not treated as pass/fail.

## Crash cases

No Python exceptions occurred in the executed stress cases.

## Targeted operator/comment cases

- `int main(){ int a = 1**+8; return 0; }` → **SYNTAX_ERROR** (PASS)
- `int main(){ int a = 1+**8; return 0; }` → **SYNTAX_ERROR** (PASS)
- `int main(){ int a = 1/**+8; return 0; }` → **LEXICAL_ERROR** (PASS)
- `int main(){ int a = 1+/**8; return 0; }` → **LEXICAL_ERROR** (PASS)
- `int main(){ int a = 1/*x*/+8; return 0; }` → **ACCEPTED** (PASS)
- `int main(){ int a = 1+/*x*/8; return 0; }` → **ACCEPTED** (PASS)
- `int main(){ int a = 1/*x*/*+8; return 0; }` → **ACCEPTED** (PASS)
- `int main(){ int a = 1*/*x*/ *8; return 0; }` → **SYNTAX_ERROR** (PASS)
- `int main(){ int a = 1+/*x*/-8; return 0; }` → **ACCEPTED** (PASS)
- `int main(){ int a = -/*x*/8; return 0; }` → **ACCEPTED** (PASS)

## Review candidates

- **ST00082 Malformed/boundary numeric literal 41: 999999999999999999999999999999999999999999999999999999999999999999**: observed `ACCEPTED`. Tests number-token boundaries and incomplete exponents/suffixes. Source: `int main(){ float a = 999999999999999999999999999999999999999999999999999999999999999999; return 0; }`
- **ST00083 Malformed/boundary numeric literal 42: 1e9999999999999999999999999999999999999999999999999999999**: observed `LEXICAL_ERROR`. Tests number-token boundaries and incomplete exponents/suffixes. Source: `int main(){ float a = 1e9999999999999999999999999999999999999999999999999999999; return 0; }`
- **ST00090 Character literal 7: "'\\q'"**: observed `LEXICAL_ERROR`. Malformed, escaped, empty, and multi-character character literals. Source: `int main(){ char c = '\q'; return 0; }`
- **ST00104 String literal 5: '"\\q"'**: observed `LEXICAL_ERROR`. Escape validity, quotes, and termination boundaries. Source: `int main(){ "\q"; return 0; }`
- **ST03669 Negative array size**: observed `ACCEPTED`. Mutates a declaration, control-flow construct, or unsupported C feature. Source: `int main(){int a[-1];return 0;}`

## Actionable phase mismatches

No layer-specific lexical expectation mismatches among the marked cases.

## How to interpret

- `ACCEPTED` means no lexical, syntax, or semantic diagnostics were produced; it does not mean the source was executed at runtime.
- `OBSERVED` cases are exploratory operator combinations. Their actual outcomes are included so you can identify surprising accepts/rejections without claiming every combination is necessarily invalid.
- `WRONG_PHASE` indicates that input was rejected, but the diagnostic came from a later compiler phase than expected (useful for lexer bugs).
- The test harness deliberately records crashes separately from normal compiler diagnostics.
