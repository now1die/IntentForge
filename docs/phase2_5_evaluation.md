# Phase 2.5 evaluation

The engine and model were frozen before the 44-case, 43-family final set was
constructed and scored. The 111 Phase 1.5 cases are a separate historical
comparison. The development experiment used separate families. All results here
measure static compiler checks and reference recovery.

## Code-only comparisons

No requirement, expected expression or test example was supplied in these runs.
Phase 2 contextual modes use their original generator. Expanded deterministic
and expanded learned share the Phase 2.5 candidate pool. The last column isolates
candidate generation on the final set.

| Configuration | Historical top 1 / top 3 | Final top 1 / top 3 | Final candidate recall |
|---|---:|---:|---:|
| Original rules | 24/88 / 24/88 | 1/30 / 1/30 | 1/30 |
| Original ML | 18/88 / 18/88 | 1/30 / 1/30 | 1/30 |
| Original hybrid | 25/88 / 25/88 | 1/30 / 1/30 | 1/30 |
| Phase 2 deterministic | 37/88 / 38/88 | 8/30 / 11/30 | 11/30 |
| Phase 2 learned | 36/88 / 38/88 | 8/30 / 11/30 | 11/30 |
| Expanded deterministic | 39/88 / 40/88 | 15/30 / 18/30 | 18/30 |
| Expanded learned, full code-only | 37/88 / 40/88 | 16/30 / 18/30 | 18/30 |

Most recovery gains come from candidate generation. Learning moved one final
case to first place and lost two top placements relative to the expanded
deterministic order in the historical cohort. It applied to comparable
candidate groups in 13 final cases. The final full code-only top-1 Wilson
interval is approximately 36%–70% and is descriptive for this curated sample.

The main final failure was missing candidates in **12/30** adjudicable cases.
A lower-ranked alternative contained the reference in **2/30** more cases.
The final code-only engine produced 64 candidates across 42 supported inputs.
**50/64** passed all compiler stages. The two non-reference top proposals among
18 adjudicable cases with proposals are reference-ordering misses. Compiler
validity and token matches carry no behavioral proof. The raw report separately
counts explicit rejected reference matches.

All 14 compiler faults were detected. Code-only logic suspicions covered
**6/18** labeled logic faults. Six of eight alerts were on labeled faults, and
two of eight valid controls raised a hypothesis. Those controls intentionally
leave a computed value unused or combine similar-looking operations differently.
All four ambiguous cases received an uncertainty or no-repair decision. There
were zero automatic edits among the 42 supported final inputs. Candidate
generation and validation averaged approximately 2.38 ms with 7.81 ms p95,
and the full code-only path averaged 4.16 ms with 9.62 ms p95 on this host.
Model loading is cached after a measured cold load of roughly 43 ms.

## Effect of supplied evidence

The same 17 cases have all three evaluated input forms. Fourteen have
reference repairs and three are valid controls. The natural language text
contains no exact answer expression on the 14 repair cases. The single
identifier supplied in a matched control's description is explicitly marked
in the data. Full code-only, natural-language and explicit results use the
same generator and model gates.

| Evidence | Top 1 / top 3 | Logic suspicions | Valid control alerts |
|---|---:|---:|---:|
| Source only | 3/14 / 3/14 | 3/14 | 1/3 |
| Description | 7/14 / 7/14 | 9/14 | 0/3 |
| Expected expression or condition | 14/14 / 14/14 | 14/14 | 0/3 |

The grammar recognized nine of the fourteen faulty descriptions and proposed
a strict reference match for **7/9**. Five unsupported descriptions produced
no match. The two recognized strict-token misses parsed to the same AST as
their references after removing spans. Their differences were redundant
parentheses. The report retains the strict scoring rule and records this as
a supplementary AST comparison.

The five public-task adaptations were **0/5** code-only. Natural guidance
matched one of four with supplied wording. Explicit input matched all four
supplied cases. The remaining adapted case lacks a scoped return or condition
requirement. These results limit claims of autonomous generalization on
externally sourced task ideas.

The explicit result measures supplied-structure repair. It offers no
independent evidence of autonomous intention recovery. Calibration and
selective coverage are kept separate from these scores. Runtime verification
has zero observations. [Model card](phase2_5_model_card.md)

[Full table](../benchmarks/reports/phase25-evaluation-v1.md) ·
[Per-category and case-level evidence](../benchmarks/reports/phase25-evaluation-v1.json)
