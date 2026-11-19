# Phase 4 evaluation

The suite uses repository-authored trusted fixtures. Fourteen semantic
families cover arithmetic, short-circuiting, nested loops, returns,
recursion, arrays, global reset, scope shadowing, runtime errors,
resource limits and unsupported constructs. The suite checked all 14
expected outcomes. It attempted 27 of 28 vectors and returned 22 scalar
observations. Five runtime or resource failures and one unsupported
program account for the other vectors. A small Python arithmetic
reference checked 144 signed division and remainder vectors, and a
closed-form triangular count checked the nested-loop family. No native
C program was run.

Seven independent repair families include four labeled repair references
and three controls or unsupported inputs. The static engine generated all
four references. Static top 1 was 3/4 and top 3 was 4/4. All six proposed
candidates passed compiler checks and were executed. Five matched their
test vectors, including all four accepted repairs and one distinct
candidate in an ambiguous coincident-argument case. One compiler-valid
candidate hit a division fault. The originals produced two matches,
one output mismatch, two runtime faults and two unsupported results.
The tests supplied matching evidence for four reference repairs. The
ambiguous case still requires a discriminating specification.

The local benchmark recorded mean/p95 semantic verification of
approximately 3.2/9.8 ms without traces and 3.6/12.8 ms with traces.
These figures average five-run medians by family and include compiler
admission. Per attempted vector averaged 2.1 ms. Mean/p95 repair
comparison was 14.6/43.1 ms in this run. Peak observed storage was eight
logical cells and peak call depth eight. The largest retained trace
had 44 entries and 8,141 bytes. Timings vary with load and the cases
do not represent the full language or arbitrary programs.

Signed arithmetic reference checks, hand-reviewed output fixtures,
and deterministic replay are separated from historical Mini-C and ML
benchmarks. No ranker was trained or selected on these cases.

```bash
OPENBLAS_NUM_THREADS=1 python -m benchmarks.phase4_vm --write
OPENBLAS_NUM_THREADS=1 python -m benchmarks.phase4_vm --check
python -m pytest -q tests/test_phase4_vm.py
```

[Machine-readable report](../benchmarks/reports/phase4-vm-v1.json)
