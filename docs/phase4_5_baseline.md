# Phase 4.5 baseline

The fetched default branch includes merged PR #7 at
`5772608c804e4d903f4e3f1a8f850bef762474a8`. The Phase 4.5 worktree
starts at that exact revision.

Baseline checks passed 613 Python tests, 25 browser tests and the
production frontend build. The original compiler suite passed all 220
cases, the 65-case keyboard/array verification reported zero unexpected
results, and the stress suite ran 3,758 inputs. Historical corpus,
training and decisions reproduced, including Phase 4. Clang 19.1.7
passed its 12-case integration benchmark.

The Phase 4 VM had no execution route. Its explicit continuation
stack and logical step, call, cell and trace budgets covered trusted
execution only. The separate Clang sandbox did not confer Mini-C
execution authority. The workbench served recorded fixtures. Static
repair ordering, source snapshots and explicit approval governed
candidate review.

The semantic inventory is signed 32-bit checked integers and bool,
with internal void calls, lexical scopes, direct calls, arrays, loops
and bounded recursion. The VM excludes float, char, string, indirect
calls, bare declarations as control bodies, void entries and full C.
