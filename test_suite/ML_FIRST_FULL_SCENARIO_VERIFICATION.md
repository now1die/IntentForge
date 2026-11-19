# ML-First Full-Scenario Verification

Run date: 2026-10-27. Results are from the project in this archive, after regenerating the
20-class model, updating the `for`-header training cases, adding comma-separated declarations,
and correcting malformed-number handling for `..5`.

## Verified results

| Test group | Result | Meaning |
|---|---:|---|
| Python repository test suite | **432 passed** | Includes the API-level screenshot repro and scenario matrix |
| General compiler corpus | **220/220** | Expected phase/result matched |
| Keyboard and array exact-repair matrix | **65/65** | Exact expected corrected source; zero crashes |
| Stress suite | **3,758 cases executed** | Completed without crashes |
| Stress expected-result statuses | **255 PASS, 0 WRONG_PHASE** | Labelled cases are behaving in the expected compiler phase |
| Stress review-only cases | **2 REVIEW_ACCEPTED, 3 REVIEW_REJECTED** | Explicitly marked for language-spec review, not counted as normal passes |
| Exploratory operator combinations | **3,498 OBSERVED** | Stored as observations, not incorrectly claimed as individual passes |

## User-reported screenshot case

Input:

```c
int main(){ int a,b; if(a.b){return 0;} }
```

The `/correct` HTTP endpoint returns status `200`, with `success: true`, one correction, and:

```c
int main(){ int a,b; if(a>b){return 0;} }
```

The parser accepts comma-separated declarations, and the ML class `KEYBOARD_GREATER_THAN`
handles the dot-to-comparison edit in the condition. A dot outside a control header is not
silently rewritten as a comparison.

## Scenarios covered by the new end-to-end matrix

The tests cover every one of the 20 trained ML classes on a packaged labelled example, plus the screenshot repro, `if` and `for` comparison typos, comma/less-than,
`8`/multiplication, `+`/assignment, colon/semicolon, missing parenthesis, array declaration
and indexing delimiter mistakes, array-call/index confusion, missing semicolon/bracket/brace,
keyword spelling, operator transposition, compound mismatched delimiters, the HTTP `/correct`
route, comma-separated declarations, ambiguous edits, and unsupported member-like syntax.

## Ambiguity is deliberately not auto-corrected

For an input such as `x == = 3;`, more than one syntactically valid interpretation may be
plausible. In that case the system preserves the original source and returns an ambiguity
status rather than inventing a semantic choice. This is intentional safe behavior.

## Re-run verification

From the project root, after installing requirements:

```powershell
.\.venv\Scripts\python.exe -m pytest -q --disable-warnings
.\.venv\Scripts\python.exe test_suite\run_test_cases.py
.\.venv\Scripts\python.exe test_suite\run_keyboard_and_array_regression.py
.\.venv\Scripts\python.exe test_suite\stress\run_stress_tests.py .
```

The model's 100% held-out score is on a controlled synthetic dataset split (1,328 train / 332
test); it must not be presented as 100% accuracy on general student programs. The scenario and
stress results above are separately measured against the test suite's expectations.
