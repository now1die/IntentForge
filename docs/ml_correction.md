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
25-class ML classifier
  ↓
ML class → candidate edit
  ↓
Compiler-native alternatives (only as safety candidates when available)
  ↓
Candidate ranking + re-lex/re-parse validation
  ↓
Apply eligible structural edits or return proposals for explicit review
```

The compiler checks Mini-C validity. The classifier chooses a repair family and
the adapter creates bounded edits.
Legacy parser recovery remains available as a source of compiler-native candidates for
ordinary syntax errors; it is not used as a special-case keyboard/array fixer. An
ambiguous program is left unchanged rather than receiving an arbitrary edit.

## Correction classes

The saved classifier has **25 classes**:

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
- `DECLARATION_SEPARATOR_ERROR`
- `DECLARATION_DOT_ERROR`
- `DECLARATION_COLON_ERROR`
- `SCALAR_ARRAY_USE_ERROR`
- `ARRAY_BRACE_INDEX_ERROR`

## Training data and evaluation

The artifact report records **2,560 training rows and 640 test rows** in a
seed-42 stratified synthetic split. The archived corpora contain 2,400 generator
records and 640 scenario records. The historical reported accuracy was 640/640.
The [generalization analysis](ml_generalization_analysis.md) gives the archive
coverage, template overlap, and independent benchmark results.

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

The compiler validates proposed edits. The safety policy allows eligible
localized structural repairs to apply automatically. Ambiguous and
potentially behavior-changing repairs remain available for explicit review.

The model artifact is `models/syntax_error_classifier.joblib`; training records are in
`datasets/syntax_corrections.jsonl` and `datasets/adversarial_scenarios.jsonl`.

## Commands

```powershell
.\.venv\Scripts\python.exe main.py --generate-dataset --dataset-size 2400
.\.venv\Scripts\python.exe main.py --train-model --dataset-size 2400
.\.venv\Scripts\python.exe main.py --predict-error examples\invalid\broken_if.mc
.\.venv\Scripts\python.exe main.py --correct examples\invalid\broken_if.mc
.\.venv\Scripts\python.exe -m pytest -q
```
