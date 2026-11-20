# Comparison normalization

The analysis normalizes atomic, compiler-typed integer identifiers and int32 literals. A reversed relational comparison flips the operator. A single outer logical negation complements it. A loop may request its induction binding as the canonical left operand, preserving the source spans of both operands.

The equivalent forms `i < n`, `n > i`, `!(i >= n)` and `!(n <= i)` all produce the same loop-progress hypothesis in dedicated tests. Those tests check the patched program against an independent arithmetic reference in Mini-C. Calls, array reads, arithmetic expressions, assignments and updates are excluded from normalization. Production normalization views the AST and does not rewrite expression order.

```sh
python -m pytest -q tests/test_phase6.py -k 'orientation or normalization'
```
