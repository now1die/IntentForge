# Phase 4 baseline

The branch starts at merged Phase 3.5 commit
`4d38f3b267d89885c420b95e1d22a88412acb6e2`. PR #6 was merged into
`phase-1-intention-benchmarking`. Baseline checks ran on that tree before
implementation changes.

- 557 Python tests passed with libclang 19.1.7. The dedicated C API
  benchmark validated 12 requests and 13 translation units.
- The production frontend built successfully. All 23 Chromium tests passed.
- Original compiler cases passed 220/220. The 65-case keyboard and array
  suite reproduced zero unexpected results and showed 45 withheld references.
- The stress suite ran 3,758 inputs. Historical audit and decision checks
  from Phase 1 through Phase 3.5 reproduced.

The AST and semantic analyzer define scoped bindings, including a separate
scope for for initializers and a shared scope for parameters and the outer
function body. Conditions and logical operations require bool. Assignment
allows same-type scalars and integer-to-float widening. The interpreter
inventory identifies which types are admitted. Parser and semantic analysis
supply no execution order or numeric overflow policy.
