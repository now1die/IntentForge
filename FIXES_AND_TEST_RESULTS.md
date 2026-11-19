# AI Compiler — Fixes and Verification Results

## Compiler fixes

The lexer in `compiler/lexer.py` has been corrected and regression tests have been added.

1. **Malformed exponent detection:** incomplete or malformed literals such as `1e+`, `1.0e+`, `.5e-`, `1e+-2`, and `1e++2` now produce a lexical `MALFORMED_NUMBER` diagnostic instead of being split into unrelated tokens and reported only by the parser.
2. **Valid number controls preserved:** valid forms such as `1e+8`, `1e-8`, `2.e2`, and `.5e-2` remain valid.
3. **Floating-point overflow:** values that convert to infinity, such as `1e999999999999999999999999`, now produce `NUMERIC_LITERAL_OUT_OF_RANGE`.
4. **Escape validation:** unknown or incomplete escapes such as `\q` and `\x4` in character/string literals are lexical errors. Supported simple escapes, octal escapes, and two-digit hexadecimal escapes continue to work. String literals additionally accept `\uXXXX` and `\UXXXXXXXX`; these Unicode escapes are not enabled in character literals.
5. **Backslash literals preserved:** valid escaped-backslash character and string literals continue to work.
6. **Operator and comment regression coverage:** the malformed expressions `1**+8` and `1+**8` remain syntax errors (without crashing), while comments between operators are handled correctly, e.g. `1+/* comment */8`.

`a.b;` remains rejected because member access is outside this project's documented Mini-C subset.

## Final test results

| Test run | Result |
|---|---:|
| Project's custom source corpus | **220 / 220 expectations matched** |
| Stress suite | **3,758 cases completed; 0 crashes** |
| Labelled stress expectations | **255 passed; 0 failed; 0 wrong-phase results** |
| Exploratory operator combinations | **3,498 recorded as OBSERVED** |
| Review-only cases | **2 accepted, 3 rejected; deliberately left for specification review** |
| Targeted lexer/parser pytest | **106 passed** |
| Full project pytest suite | **380 passed, 3 warnings** |

The stress suite's 3,758 observed results were: 82 accepted programs, 1,267 lexical-error cases, 1,687 syntax-error cases, and 722 semantic-error cases. Inputs designed to be invalid are expected to be rejected; those rejections are not test-harness failures.

The three pytest warnings are scikit-learn `InconsistentVersionWarning` messages: the available runtime is using scikit-learn 1.8.0 to load a model created with 1.7.2, while the project pins 1.7.2. The tests passed, but a matching dependency environment should be used for deployment.

## Re-run the tests

Run these commands from the project root after installing the requirements:

```bash
python -m pip install -r requirements.txt
python test_suite/run_test_cases.py
python test_suite/stress/run_stress_tests.py .
pytest -q
```

For API keys, copy `.env.example` to `.env` and fill in the required values locally. The delivered project archive intentionally excludes `.env` so credentials are not copied into the download.
