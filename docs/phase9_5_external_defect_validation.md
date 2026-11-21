# External defect validation

| Documented adaptation | Independently confirmed behavior | Phase 9.5 holdout |
| --- | --- | --- |
| Exclusive multiple sum | The defect includes an upper endpoint divisible by three or five. [Upstream fix](https://github.com/TheAlgorithms/JavaScript/commit/90891b56578d7ae6ac4c8a255da507db613bc6f5) | Exact repair |
| Gregorian day difference | Flooring the combined fractional expression changes the ordinal. [Upstream fix](https://github.com/TheAlgorithms/JavaScript/commit/f13eec1bbb94484912d10a4e5376aacf533b3de6) | No repair |
| Recursive search upper bound | An absent key above the largest cell reaches an out-of-range index. [Upstream fix](https://github.com/TheAlgorithms/Java/commit/d22420fea8d7b05d02e42111d9bc5e24137e907f) | No repair |
| Expanding search boundary | The searched interval misses legal endpoints and exposes raw insertion indices. [Upstream fix](https://github.com/TheAlgorithms/Java/commit/55f551b17bd0c48b7cb1ba7ecfb7092803c7a150) | No repair |
| Smith composite domain | The original can classify zero as Smith. [Upstream fix](https://github.com/TheAlgorithms/Java/commit/e79b0f106477774020d4c5c2738f0854ff3d2444) | No repair |

One of five adaptations received an exact passing repair. The 95% Wilson
interval is 3.6% to 62.4%. Four defective programs produced completed mismatches
and one stopped with a runtime bounds issue. The result reflects a small
educational corpus with independent executable references and no external
human adjudication. Source replays cover the defects and fixes directly.
[Upstream observations](../benchmarks/reports/phase95-upstream-v1.json) ·
[Isolated validation](../benchmarks/reports/phase95-live-v1.json)
