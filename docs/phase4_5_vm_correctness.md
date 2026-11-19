# Phase 4.5 Mini-C correctness

The lexer now emits a located `NUMERIC_LITERAL_OUT_OF_RANGE` diagnostic for decimal literals beyond the host conversion limit. Previously a very large literal raised a Python exception before the compiler could produce a result. The regression fixture uses 6,000 digits and verifies a bounded diagnostic excerpt.

The semantic suite checks 240 seeded input tuples against independently computed arithmetic results. Targeted programs exercise branch and short-circuit order, index and update order, nested control flow, array isolation, lexical shadowing, recursive and iterative equivalence, deterministic traces and state reset. A fault test checks that unwound frames release their logical cells. The test seed and assertion output identify a generated input for reproduction.

The separate final benchmark exercises 14 semantic families and 28 supplied vectors. Another 216 seeded input vectors check signed quotient/remainder and closed-form loop and recursion results. Runtime faults and admission limits are covered by independently specified diagnostic codes. The independent references are mathematical and fixture-based. Clang remains a separate analysis engine.

```sh
python -m pytest -q tests/test_phase45_semantics.py tests/test_phase4_vm.py
python -m benchmarks.phase45_vm --check
python -m benchmarks.phase4_vm --check
```

See [supported Mini-C](phase4_supported_language.md) for interpretation limits and [evaluation](phase4_5_evaluation.md) for results.
