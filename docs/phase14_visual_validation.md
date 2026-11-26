# Visual comparison

Compared the available individual Compiler, Intention and Research Lab mockups and the cropped header against browser captures. The Examples & Learning mockup was absent from the supplied images. That page follows the written layout requirements.

The angled transition, cream active navigation, dark burgundy Monaco, paper workspace, rounded borders and burgundy/rose graphs carry across the product. The implementation uses a tighter typography scale, a lighter paper texture, original computing illustrations and operational controls. The illustrations omit scenic backgrounds. The graph follows the actual submitted program and the rendered blocks differ from the reference diagram. The status area omits the reference's account and notification icons because the application has no account or notification features.

| Workspace | Genuine Chromium captures |
| --- | --- |
| Compiler | [Success](../audit/phase14/compiler-success.png), [diagnostic and fix](../audit/phase14/compiler-correction.png), [AST](../audit/phase14/compiler-ast.png), [symbols](../audit/phase14/compiler-symbols.png) |
| Intention | [Test cases](../audit/phase14/intention-test-cases.png), [suggested repair](../audit/phase14/intention-suggestion.png), [verified repair](../audit/phase14/intention-verified.png), [ambiguity](../audit/phase14/intention-ambiguous.png) |
| Research Lab | [Control-flow graph](../audit/phase14/research-cfg.png), [program state and benchmarks](../audit/phase14/research-state-benchmarks.png) |
| Examples & Learning | [Library](../audit/phase14/examples.png) |
| Startup and small displays | [Backend offline](../audit/phase14/backend-offline.png), [responsive](../audit/phase14/responsive.png) |
| Baseline | [Phase 13 Compiler](../audit/phase14/baseline-compiler.png) |

To recreate the screenshots, set `INTENTFORGE_PRODUCT_CAPTURES` to an absolute directory and run `npm --prefix frontend test -- phase14.spec.ts`. The verified repair capture requires the restricted worker.
