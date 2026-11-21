# Semantic robustness

The archived failures involve the modulo-slot counter and the descending
credit counter. Each lost its repair when the original relation was written
with reversed operands or when a nested unused declaration scope was inserted
before the return. The Mini-C VM observed the same original behavior on the
designated vectors in all four comparisons.

The first differing analysis steps were the left-only induction check and
the fixed top-level statement count in Phase 8.5. Phase 9 identifies the
induction variable by binding and uses the CFG to find the loop and its exit.
The replay records each source, binding IDs, CFG blocks and edges, reaching
definitions at loop headers and returns, and the repair decisions on each
snapshot. All four transformations now retain the repair category and a
compiler-valid candidate with the same observed repair effect on the vectors.

Across transformations, category, observed repair effect, compiler validity
and explicit approval are the relevant properties. Source locations and
candidate IDs depend on the original source snapshot.
[Archived reconstructions and expanded comparisons](../benchmarks/reports/phase9-static-v1.json)
