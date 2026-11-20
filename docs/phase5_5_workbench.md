# Phase 5.5 workbench

Choose **Phase 5.5 precision gates** in the Intention tab. The structural scan displays surviving hypotheses and a separate list of withheld hypotheses. Each withheld row shows its supporting signal and the counter-evidence or missing requirement. Candidate diffs, compiler validity, static ordering and explicit approval remain available on reviewable alternatives.

In the restricted local behavioral panel, enable candidate comparison, Phase 5 repair and probes, then the precision gates. The panel keeps static rank and observed order visible. It also shows per-vector outcomes, probe costs, alternatives and multiple matches. Pending approvals disappear when the source or profile changes.

```sh
INTENTFORGE_PHASE55_CAPTURES="$PWD/audit/phase55" npm --prefix frontend test -- phase55.spec.ts
```

[Withheld evidence screenshot](../audit/phase55/withheld-evidence.png) · [Isolated ambiguity screenshot](../audit/phase55/isolated-ambiguity.png)
