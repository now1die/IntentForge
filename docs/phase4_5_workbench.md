# Interactive Mini-C workbench

With the [local service](phase4_5_execution_isolation.md) available, open **Interactive behavioral verification** in Mini-C mode. Select an entry point from the latest AST suggestions or type its name. Edit or paste reusable JSON test vectors with signed 32-bit integer or Boolean arguments and expected results. Set limits and tracing as needed, then run the verification. The result table gives each supplied input, expected value, observed value and outcome. Original runtime locations link to the source editor.

Turn on **Compare repair candidates** and optionally provide an explicit expected return expression. Review the side-by-side source preview, static position and observed outcomes before clicking **Apply reviewed behavioral repair**. Add a probe input to the editable test JSON and specify its expected value before using it as a test.

On the default deployment, the section reports that interactive execution is disabled. The recorded **Behavioral verification** section remains usable. In C/Clang mode, the workbench shows analysis and explains that execution is unavailable.

- [Desktop live repair review](../audit/phase4_5/live-review.png)
- [Mobile candidate disagreement](../audit/phase4_5/live-probes-mobile.png)

Reproduce these captures from a running verified socket.

```sh
npm --prefix frontend ci
(cd frontend && npx playwright install chromium)
INTENTFORGE_PHASE45_CAPTURES="$PWD/audit/phase4_5" npm --prefix frontend test -- phase45.spec.ts
```
