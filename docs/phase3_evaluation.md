# Phase 3 evaluation

The C analysis benchmark runs through the real FastAPI route and the
isolated Clang 19.1.7 worker. All six valid requests parsed, all six
diagnostic requests returned the expected classification, and all six
diagnostic anchors matched the checked physical line and UTF-16 column.
The 12 requests contained 13 translation units. All 13 exposed the
expected cursor kind, including units with recovered ASTs. All 12 HTTP
requests returned their structured responses. The sample mean was 76 ms
and p95 was 119 ms, including worker startup but excluding capability
discovery. Timings are machine-dependent. Disabled capability returned
`unavailable` while Mini-C analysis returned HTTP 200.

Fixture coverage includes pointer types, multidimensional subscripts,
structures, unions, enums, aliases, function pointers, recursion, macros,
dynamic-memory function declarations, numeric types, casts, control
flow, scopes, and multiple source files. These are analysis adapter
fixtures. The benchmark has no execution or repair accuracy metric.

```bash
python -m pytest -q tests/test_clang_backend.py
python -m benchmarks.clang_analysis --check
npm --prefix frontend test -- clang.spec.ts
```

See the [machine-readable report](../benchmarks/reports/clang-analysis-v1.json)
and [browser evidence](../audit/phase3).
