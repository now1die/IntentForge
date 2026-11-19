# Phase 2.5 intention workflow

The **Intention** tab offers three analysis modes.

| Mode | Input | Evidence shown |
|---|---|---|
| Code only | Mini-C source | Compiler facts and bounded contextual hypotheses |
| Natural-language requirement | Source and a supported description | An interpreted operation with its code anchor, or an unsupported-wording indication |
| Explicit specification | Source and a selected return or condition expression | Structural comparison with the supplied expression |

**Use entered fields** selects a mode from the form for existing workbench
users. Select a proposal to inspect its span, evidence, assumptions,
compiler result, safety reason, and diff. An edit to the source, mode or
requirement invalidates the preview. A compiler-valid proposal remains
review-only. Behavior has no runtime oracle in this phase.

Examples of supported wording include:

- `Return the product of unit_price and count`
- `Return amount decremented by debit`
- `Return whether score is between low and high inclusive`
- `Return whether both ready and work is at least 3`
- `Return the minimum of left and right` with a simple existing two-return selection
- `Return the result of calling combine with first and second`

Requirement normalization is grammar-based. Conditions with several possible
locations need a selected ordinal. Unrecognized wording receives a separate
status. A matching explicit or supported natural requirement suppresses
unrelated code-only speculation. Inline expression syntax belongs to the
explicit mode.

```sh
curl -sS http://127.0.0.1:8000/v1/intention-analysis \
  -H 'Content-Type: application/json' \
  --data '{"code":"bool ready(int work){return work<3;}","mode":"natural_language","requirement":{"description":"Return whether work is at least 3"}}'
```

Use `"mode":"code_only"` with no requirement, or use `"mode":"explicit"`
with `"requirement":{"return_expression":"work>=3"}`. Omit the mode for the
earlier request behavior. The additive `requirement_status` field reports
recognition for explicit mode requests. Model paths remain deployment data.
Compatibility, approval and changed-source behavior are tested through the API
and the browser.

[Fresh workbench screenshots](../audit/phase2_5/README.md)
