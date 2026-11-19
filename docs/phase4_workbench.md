# Workbench behavioral demonstrations

Open **Behavioral verification** in Mini-C mode and select **Load
trusted example**. The workbench displays recorded interpreter
observations for a repair comparison, ambiguous alternatives, a
division fault and a bounded loop. It shows supplied vectors, actual
outputs, runtime diagnostics, trace locations and skipped candidates.

The display follows the exact loaded editor snapshot. An edit hides
recorded results. Switching to Clang hides the Mini-C demonstration.
Candidate source previews are read-only and do not apply the change.
Unrestricted execution is unavailable in the workbench.

```bash
python -m benchmarks.phase4_vm --write
npm --prefix frontend run build
INTENTFORGE_PHASE4_CAPTURES="$PWD/audit/phase4" npm --prefix frontend test -- phase4.spec.ts
```

[Real browser captures](../audit/phase4)
