# ML-First Syntax Correction

## Architecture

The active repair path is ML-first. The lexer/parser (and, for syntactically valid
array-call mistakes, semantic analysis) supplies diagnostics and context features.
The classifier predicts a repair class; a class-conditioned adapter materializes a
small edit; the compiler then re-lexes/re-parses and, where relevant, re-runs semantic
analysis before the edit can be applied.

```text
Source
  ↓
Lexer / Parser / Semantic diagnostics
  ↓
Structured compiler context
  ↓
20-class ML classifier
  ↓
ML class → candidate edit
  ↓
Compiler-native alternatives (only as safety candidates when available)
  ↓
Candidate ranking + re-lex/re-parse validation
  ↓
Apply one uniquely supported correction, or leave ambiguity unresolved
```

The compiler remains the correctness authority. The ML classifier does not freely
rewrite the source: it chooses a repair family, and the adapter creates bounded edits.
Legacy parser recovery remains available as a source of compiler-native candidates for
ordinary syntax errors; it is not used as a special-case keyboard/array fixer. An
ambiguous program is left unchanged rather than receiving an arbitrary edit.

## Correction classes

The saved classifier has **20 classes**:

- `INSERT_SEMICOLON`
- `INSERT_RPAREN`
- `INSERT_LPAREN`
- `INSERT_RBRACKET`
- `INSERT_RBRACE`
- `DELETE_EXTRA_TOKEN`
- `REPLACE_BRACKET`
- `REPLACE_OPERATOR`
- `CORRECT_KEYWORD`
- `KEYBOARD_GREATER_THAN`
- `KEYBOARD_LESS_THAN`
- `KEYBOARD_MULTIPLY`
- `KEYBOARD_ASSIGNMENT`
- `KEYBOARD_SEMICOLON`
- `KEYBOARD_LPAREN`
- `KEYBOARD_RPAREN`
- `ARRAY_DECLARATION_ERROR`
- `ARRAY_INDEX_ERROR`
- `ARRAY_CALL_ERROR`
- `REPAIR_MISMATCHED_DELIMITER`

## Training data and evaluation

The packaged dataset contains **2,400 compiler-validated synthetic records**, balanced at
83 examples per class. Training uses a stratified 80/20 split with `random_state=42`:
**1,328 training records and 332 held-out records**.

The measured held-out accuracy is **1.000 on this controlled synthetic split**. This is
not a claim of 100% performance on arbitrary student code; the real-scenario regression
matrix and parser-validated end-to-end tests are reported separately in
`test_suite/ML_FIRST_FULL_SCENARIO_VERIFICATION.md`.

A record stores original and corrupted source, the correction-class label, compiler
diagnostic, structured error context, candidate information, and the ground-truth edit.
The training source is generated from known-valid Mini-C examples and the ground-truth
repair must restore a valid program.

## Examples

| Input | Predicted class | Correction |
|---|---|---|
| `if(x.5)` | `KEYBOARD_GREATER_THAN` | `.` + `5` → `> 5` |
| `if(x,5)` | `KEYBOARD_LESS_THAN` | `,` → `<` |
| `for(i=0;i.5;i++)` | `KEYBOARD_GREATER_THAN` | `.5` → `> 5` in the for-header |
| `x 8 8` | `KEYBOARD_MULTIPLY` | first `8` → `*` |
| `int x + 5;` | `KEYBOARD_ASSIGNMENT` | `+` → `=` |
| `int x: ...` | `KEYBOARD_SEMICOLON` | `:` → `;` |
| `if 9x > 5)` | `KEYBOARD_LPAREN` | `9` → `(` |
| `int arr(5]` | `ARRAY_DECLARATION_ERROR` | `(` → `[` |
| `arr(i]` | `ARRAY_INDEX_ERROR` | `(` → `[` |
| `arr(i)` when `arr` is declared as an array | `ARRAY_CALL_ERROR` | call delimiters → index delimiters |
| `if ((x > 5] {` | `REPAIR_MISMATCHED_DELIMITER` | coordinated delimiter repair |

Comma-separated scalar declarations such as `int a,b;` are now supported by the parser.
A dot-to-comparison repair is only proposed when it is inside a control header; an
unsupported member-like expression such as `a.b;` is not guessed into a comparison.

## Features

The classifier receives structured compiler-derived features: phase, grammar context,
current/previous/next token types and lexemes, expected-token signature, delimiter depth,
nearby source context, keyword similarity, lexical diagnostic metadata, and a compact
repair signature. The model is a Scikit-learn pipeline: `DictVectorizer` followed by
balanced `LogisticRegression`.

## Validation rule

Every proposed edit is checked by the actual Mini-C compiler. A syntactically valid
candidate is re-parsed, and semantic repairs are re-analysed. The system does not claim
that a prediction probability alone proves a repair is correct. If two plausible edits
produce valid programs and the system cannot distinguish them reliably, it leaves the
original code unchanged and reports ambiguity.

The model artifact is `models/syntax_error_classifier.joblib`; training records are in
`datasets/syntax_corrections.jsonl`.

## Commands

```powershell
.\.venv\Scripts\python.exe main.py --generate-dataset --dataset-size 2400
.\.venv\Scripts\python.exe main.py --train-model --dataset-size 2400
.\.venv\Scripts\python.exe main.py --predict-error examples\invalid\broken_if.mc
.\.venv\Scripts\python.exe main.py --correct examples\invalid\broken_if.mc
.\.venv\Scripts\python.exe -m pytest -q
```
