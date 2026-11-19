# Using intention analysis

Open the **Intention** tab in the workbench. Supply a function if the program has
multiple functions, then enter a return expression, a condition, or a description.
A one-based location selects among multiple returns or supported conditions in
source order. Structured expressions use Mini-C syntax. The description parser
recognizes `return the sum of a and b` and `return the square of x`.
It can also interpret `return the total cost` when a direct declaration
uniquely multiplies the `price` and `quantity` parameters, or `eligibility
begins at 18` when an integer `age` guard has an affirmative branch.
Other wording is retained for review. Function names by
themselves supply no requirement.

For example, given `int square(int n){return n+n;}`, enter `n * n` in
**Return expression**. The result reports a structural mismatch. Select a
candidate to compare its edits, and choose **Apply Reviewed Intention Repair**
to change the source.

| Finding | Evidence |
|---|---|
| Compiler-detected error | A diagnostic from Mini-C's lexer, parser, or semantic analyzer |
| Specification-supported suspicion | The AST of the selected expression differs from the requirement |
| Unverified hypothesis | A narrow AST pattern, such as an immediately computed value followed by a parameter return |
| Unsupported Mini-C construct | Recognized out-of-subset syntax such as a pointer declaration |
| No supported mismatch found | The available evidence yields no supported mismatch, or the requested expression matches structurally |

**Evidence** sections identify the observed span, scope, type, binding,
signature, diagnostic, or supplied requirement. **Hypothesis** explains the
assumption behind a candidate. A compiler-valid result passed lexical, syntax,
and semantic checks. An insufficient-context or ambiguous result preserves
multiple interpretations for review. A raw model margin orders comparable
binding alternatives. Behavioral verification remains unavailable.

Optional evidence vectors take the described function's number of arguments and
use integer or Boolean scalars. The endpoint records them but has no execution
oracle. Ambiguous function or expression locations return guidance instead of
guessing. Invalid specification syntax returns HTTP 422. Requests that exceed
token or nesting limits receive HTTP 413. Input is capped at 24,000 characters,
3,000 tokens, and 24 attempted candidate edits. There is no user-controlled
execution or arbitrary model path in the endpoint.

## API example

Start the existing Uvicorn backend, then run:

```sh
curl -sS http://127.0.0.1:8000/v1/intention-analysis \
  -H 'Content-Type: application/json' \
  --data '{"code":"int square(int n){return n+n;}","requirement":{"function":"square","return_expression":"n*n"},"include_context":true}'
```

Omit `include_context` for candidate and diagnostic output. The original
`/analyze`, `/correct`, `/correction-options`, and `/validate-correction`
contracts remain available.

## Reproduce the frontend check

```sh
npm --prefix frontend ci
npm --prefix frontend run build
npm --prefix frontend exec -- playwright install chromium
npm --prefix frontend test
```

Keep the Python environment active so Playwright can start FastAPI.
`PLAYWRIGHT_CHROMIUM_EXECUTABLE` can select a system Chromium installation.
