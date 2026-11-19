# Phase 2.5 workbench captures

These screenshots come from Playwright against the real local FastAPI and
Vite application. They cover changes made in Phase 2.5. Ollama was offline.
The [capture metadata](capture-metadata.json) records the exact engine
revision, source, mode, requirement, browser and viewport for every PNG.

- [Code-only review](01-code-only-review.png)
- [Natural-language minimum/maximum review](02-language-review.png)
- [Unsupported requirement wording](03-unsupported-requirement.png)
- [Explicit specification on mobile](04-explicit-mobile.png)

To reproduce with the Python environment active and frontend dependencies
installed, run the evidence spec from the frontend directory:

```sh
npm exec -- playwright test --config playwright.evidence.config.ts phase25
```

Set `PLAYWRIGHT_CHROMIUM_EXECUTABLE` to use an installed Chromium binary.
