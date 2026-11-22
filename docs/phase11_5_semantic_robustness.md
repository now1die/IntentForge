# Semantic robustness

Both Phase 11 unused-shadow fixes are preserved. The evaluator records original and rewritten sources, lexical binding identities, CFG evidence and candidate categories for those diagnostics.

The replay compares candidate categories and typed observed effects under alpha renaming, comparison reversal, safe parentheses, equivalent latches, nested and unused-shadow scopes, harmless temporaries and declaration-order changes. Every emitted transformed candidate must compile, require approval and match the original text at its own edit spans. Candidate identities may vary with the source. [Metamorphic report](../benchmarks/reports/phase115-static-v1.json)
