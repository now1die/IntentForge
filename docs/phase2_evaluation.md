# Phase 2 evaluation

The benchmark reuses the Phase 1 compiler and correction adapters and preserves
the 111 previously evaluated cases as historical. A separate frozen
32-case cohort was reviewed before evaluation and kept out of fitting and model
selection. One provisional case was excluded before initial scoring for a
historical normalized-template collision. The remaining exact and near-template
checks passed. The 32 cases represent source families authored with AI
assistance for this evaluation, so results are exploratory.

## Candidate generation and ranking

| Cohort and configuration | Top 1 | Top 3 | Candidate recall | Top 1 when answer generated |
|---|---:|---:|---:|---:|
| Historical rules | 24/88 | 24/88 | 24/88 | 24/24 |
| Historical original ML | 18/88 | 18/88 | 18/88 | 18/18 |
| Historical original hybrid | 25/88 | 25/88 | 25/88 | 25/25 |
| Historical context deterministic | 37/88 | 38/88 | 38/88 | 37/38 |
| Historical context learned | 36/88 | 38/88 | 38/88 | 36/38 |
| Historical full intention | 36/88 | 38/88 | 38/88 | 36/38 |
| Final rules | 2/19 | 2/19 | 2/19 | 2/2 |
| Final original ML | 0/19 | 0/19 | 0/19 | 0/0 |
| Final original hybrid | 0/19 | 0/19 | 0/19 | 0/0 |
| Final context deterministic | 5/19 | 9/19 | 9/19 | 5/9 |
| Final context learned | 6/19 | 9/19 | 9/19 | 6/9 |
| Final full intention | 16/19 | 19/19 | 19/19 | 16/19 |

The context deterministic and context learned modes receive the same candidate
pool without user requirements. Their difference isolates learned ranking.
The full mode additionally receives the frozen cohort's explicit requirements
where supplied, so its gain also reflects that extra evidence. Historical
cases carry no structured input for this comparison. Candidate recall counts
an accepted token sequence anywhere in the bounded output. Top-1, top-3 and
known-intention recovery use the supported, unambiguous cases with an accepted
reference. The original modes inspect proposals for the first diagnostic.
The new generator can also join two independently supported edits. The model
has mixed ranking effects by cohort.

The full mode produced a fully compiler-valid top proposal in 21/21 final
cases with proposals and 51/52 historical cases with proposals. Accepted
final repairs usable in the workbench rose from 3/19 for the original UI
path to 19/19 in the new section. Three final cases needed a lower
ranked option. They involved nested scope binding, an extra function argument,
and resolving a declaration initializer. Historical misses concentrated
where candidate generation had no supported repair, including unsupported
malformed operators and logic cases without a structured requirement.

## Logic detection and uncertainty

The full mode surfaced structural mismatches on 9/9 specified logic faults.
The compiler alone detected 13/13 final compiler faults. No final control
received a specification-mismatch finding (0/7, with two controls supplying
requirements). One control received an unverified heuristic alert (1/7).
All three final ambiguous cases caused abstention from automatic edits.
The new endpoint automatically edited 0/31 supported final inputs and
0/104 supported historical inputs. Runtime-equivalence and false-safe rates
have zero observations.

On the 19 adjudicable final inputs, inspecting the first available proposal
gave 19/19 coverage and 16/19 reference accuracy. Restricting review to
strong supplied evidence gave 10/19 coverage with 10/10 reference accuracy.
These are evidence policies, with no fitted confidence threshold. The
illustrative Wilson interval for the full cohort's 16/19 is 62.4%–94.5%.
The small, purposive sample limits inference to this evaluation. Relative
model margins have no calibrated probability interpretation.

Run `python -m benchmarks.phase2_evaluate --check` for consistent decisions
and `python -m benchmarks.phase2_evaluate --out /tmp/intentforge-phase2` for
fresh timing samples. Raw observations, per-category denominators, and
coverage are in the [JSON](../benchmarks/reports/phase2-evaluation-v1.json).
See the [Markdown report](../benchmarks/reports/phase2-evaluation-v1.md) for
mean and p95 inference time by mode.
