# Phase 4 architecture

The VM uses the existing Mini-C parser, semantic analyzer and source-located
AST. The admission pass rejects compiler diagnostics and checks every AST node
against the execution inventory before interpreting.

1. `vm.interpreter.prepare` admits source and indexes direct function names.
2. `Execution` allocates frames and environments separate from compiler data.
   An explicit stack drives generators representing pending expression,
   statement and function operations. Mini-C recursion does not consume a
   corresponding Python call stack.
3. `MiniCOracle` checks the entry signature, executes each typed vector from
   fresh state, and returns Phase 3.5 evidence with additive runtime details.
4. `analyze_with_behavior` runs the existing v4 static pipeline, then
   compares the original with compiler-valid alternatives for trusted callers.
5. `benchmarks.phase4_vm` regenerates curated observations displayed by
   the workbench. The frontend and HTTP service do not execute source.

The runtime steps are deterministic. Wall-clock latency is collected by
the benchmark independently. Compiler ASTs and symbol tables remain read-only.
