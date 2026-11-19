# Fresh Phase 1 workbench evidence

Captured from `a62fa2c28a403fb613cc63075660b03445757dd3` using Chromium
156.0.8078.79, Playwright, the local Vite frontend, and the real FastAPI
backend with the bundled classifier. Ollama was offline. The capture
contains no mocked requests or generated images. The desktop viewport
is 1440 × 900 unless a row specifies a different size. The app's layout is
the existing workbench.

| Screenshot | What the application shows |
|---|---|
| [01 — Main workbench](01-main-workbench.png) | Default Mini-C source, editor, and analysis panel |
| [02 — Safe structural repair](02-safe-structural.png) | Missing control parenthesis, validated with `LOW_RISK_STRUCTURAL`, ready for the user's apply action |
| [03 — Review required](03-review-required.png) | Operator change is withheld, with original source, proposed edit, and the safety reason visible |
| [04 — Ambiguous intention](04-ambiguous-intent.png) | Two distinct compiler-valid choices for adjacent return operands, with no automatic mutation |
| [05 — Before and after](05-before-after.png) | The original dot operator in the editor, the selected greater-than preview, and compiler/ML explanation |
| [06a — Syntax diagnostics](06a-syntax-diagnostics.png) | Parser diagnostic generated from the missing parenthesis |
| [06b — Semantic diagnostics](06b-semantic-diagnostics.png) | Undefined reference to `missing` from actual semantic analysis |
| [07 — Mobile](07-mobile.png) | Stacked workbench at 390 × 844 |
| [08 — Desktop](08-desktop.png) | Editor and analysis at 1440 × 900 with actual symbol-table output |

The [capture metadata](capture-metadata.json) records the exact source,
viewport, workbench status, browser, and revision for every PNG.

To reproduce from a checkout, install Python and frontend dependencies
as described in the [main README](../../README.md), activate the Python
environment, and run:

```sh
cd frontend
npm exec -- playwright test --config playwright.evidence.config.ts
```

Set `PLAYWRIGHT_CHROMIUM_EXECUTABLE` to a system Chromium binary if using
one. Otherwise install Playwright Chromium. The Playwright configuration
starts the local backend and frontend. Set `INTENTFORGE_EVIDENCE_DIR` to a
different output directory if retaining the committed PNGs.
