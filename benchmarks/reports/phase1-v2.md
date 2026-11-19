# Phase 1 benchmark

111 frozen cases, corpus v2, seed 42.

- ML-only top-1 matches missed by rule-based correction: seed-declaration, seed-indexing, v2-punctuated-decl, v2-array-index-call.
- Rule-based top-1 matches missed by ML-only correction: seed-ambiguous-condition, seed-interleaved-declaration-semicolon, v2-loop-accumulator, v2-void-early, v2-vec-global, v2-after-break, v2-after-continue, v2-while-nested, v2-for-body-closer, v2-mismatched-while, v2-argument-comma, v2-ambiguous-loop-return.
- Hybrid top-1 matches missed by ML-only correction: seed-ambiguous-condition, v2-loop-accumulator, v2-void-early, v2-after-break, v2-after-continue, v2-while-nested, v2-mismatched-while, v2-argument-comma, v2-ambiguous-loop-return.
- 18 valid Mini-C cases contained specification-level logic errors. General intent detection is unsupported.
- Behavioral observations are reported separately from compiler validation and token matches.

## Rule Based

| Metric | Result |
|---|---:|
| detection precision | 77/77 |
| detection recall | 77/95 |
| compiler fault detection recall | 77/77 |
| classification accuracy | N/A (0 eligible) |
| exact correction match | 23/88 |
| top 1 repair accuracy | 24/88 |
| top 3 repair accuracy | 24/88 |
| compiler valid repair rate | 32/42 |
| intention recovery accuracy | 24/88 |
| incorrect repair rate | 2/26 |
| unknown intent rate | 62/88 |
| behavioral test success | N/A (0 eligible) |
| automatic repair rate | 19/95 |
| automatic edit count | 19/104 |
| automatic abstention rate | 76/95 |
| approval required rate | 23/95 |
| workbench correct proposals | N/A (0 eligible) |
| unsafe provider rejection rate | 0/95 |
| unapplied safety review rate | 23/95 |
| ambiguous case abstention rate | 7/7 |
| automatic intended repair rate | 18/88 |
| regression count | 0/9 |
| average correction latency ms | 4.20 ms (285 samples) |
| p95 correction latency ms | 11.75 ms (285 samples) |

| Split | Detection recall | Top 1 | Top 3 | Approval required |
|---|---:|---:|---:|---:|
| evaluation | 20/28 | 9/26 | 9/26 | 6/28 |
| phase_1_5_holdout | 57/67 | 15/62 | 15/62 | 17/67 |

| Category | Detection recall | Top 1 | Top 3 | Compiler valid |
|---|---:|---:|---:|---:|
| ambiguous intent | 7/7 | N/A (0 eligible) | N/A (0 eligible) | 5/7 |
| array indexing | 4/6 | 0/6 | 0/6 | 0/1 |
| array indexing or declaration | 2/2 | 0/2 | 0/2 | N/A (0 eligible) |
| incorrect arithmetic | 1/2 | 0/2 | 0/2 | 1/1 |
| incorrect comparison | 0/1 | 0/1 | 0/1 | N/A (0 eligible) |
| incorrect condition | 3/5 | 0/5 | 0/5 | N/A (0 eligible) |
| incorrect conditional | 0/1 | 0/1 | 0/1 | N/A (0 eligible) |
| incorrect delimiter | 5/5 | 4/5 | 4/5 | 4/4 |
| incorrect operator | 6/8 | 4/8 | 4/8 | 4/4 |
| incorrect return | 3/4 | 0/4 | 0/4 | 2/2 |
| incorrect variable reference | 4/5 | 0/5 | 0/5 | N/A (0 eligible) |
| invalid declaration | 6/6 | 0/6 | 0/6 | 0/2 |
| missing or incorrect return | 1/1 | 0/1 | 0/1 | N/A (0 eligible) |
| missing or mismatched brackets | 2/2 | 2/2 | 2/2 | 2/2 |
| missing semicolon | 13/13 | 13/13 | 13/13 | 13/13 |
| multiple errors | 5/5 | 0/5 | 0/5 | 0/3 |
| type mismatch | 6/6 | 0/6 | 0/6 | N/A (0 eligible) |
| unsupported minic | N/A (0 eligible) | N/A (0 eligible) | N/A (0 eligible) | N/A (0 eligible) |
| valid control | N/A (0 eligible) | N/A (0 eligible) | N/A (0 eligible) | N/A (0 eligible) |
| valid syntax wrong logic | 0/4 | 0/4 | 0/4 | N/A (0 eligible) |
| variable declaration | 1/1 | 0/1 | 0/1 | 0/1 |
| wrong function argument | 5/6 | 1/6 | 1/6 | 1/2 |
| wrong variable reference | 3/5 | 0/5 | 0/5 | N/A (0 eligible) |

## Existing Ml

| Metric | Result |
|---|---:|
| detection precision | 77/77 |
| detection recall | 77/95 |
| compiler fault detection recall | 77/77 |
| classification accuracy | 20/28 |
| exact correction match | 18/88 |
| top 1 repair accuracy | 18/88 |
| top 3 repair accuracy | 18/88 |
| compiler valid repair rate | 20/22 |
| intention recovery accuracy | 18/88 |
| incorrect repair rate | 0/18 |
| unknown intent rate | 70/88 |
| behavioral test success | N/A (0 eligible) |
| automatic repair rate | 5/95 |
| automatic edit count | 5/104 |
| automatic abstention rate | 90/95 |
| approval required rate | 12/95 |
| workbench correct proposals | N/A (0 eligible) |
| unsafe provider rejection rate | 0/95 |
| unapplied safety review rate | 12/95 |
| ambiguous case abstention rate | 7/7 |
| automatic intended repair rate | 5/88 |
| regression count | 0/9 |
| average correction latency ms | 3.97 ms (285 samples) |
| p95 correction latency ms | 9.34 ms (285 samples) |

| Split | Detection recall | Top 1 | Top 3 | Approval required |
|---|---:|---:|---:|---:|
| evaluation | 20/28 | 10/26 | 10/26 | 4/28 |
| phase_1_5_holdout | 57/67 | 8/62 | 8/62 | 8/67 |

| Category | Detection recall | Top 1 | Top 3 | Compiler valid |
|---|---:|---:|---:|---:|
| ambiguous intent | 7/7 | N/A (0 eligible) | N/A (0 eligible) | 2/2 |
| array indexing | 4/6 | 1/6 | 1/6 | 1/1 |
| array indexing or declaration | 2/2 | 1/2 | 1/2 | 1/1 |
| incorrect arithmetic | 1/2 | 0/2 | 0/2 | N/A (0 eligible) |
| incorrect comparison | 0/1 | 0/1 | 0/1 | N/A (0 eligible) |
| incorrect condition | 3/5 | 0/5 | 0/5 | N/A (0 eligible) |
| incorrect conditional | 0/1 | 0/1 | 0/1 | N/A (0 eligible) |
| incorrect delimiter | 5/5 | 1/5 | 1/5 | 1/1 |
| incorrect operator | 6/8 | 4/8 | 4/8 | 4/4 |
| incorrect return | 3/4 | 0/4 | 0/4 | N/A (0 eligible) |
| incorrect variable reference | 4/5 | 0/5 | 0/5 | N/A (0 eligible) |
| invalid declaration | 6/6 | 1/6 | 1/6 | 1/1 |
| missing or incorrect return | 1/1 | 0/1 | 0/1 | N/A (0 eligible) |
| missing or mismatched brackets | 2/2 | 2/2 | 2/2 | 2/2 |
| missing semicolon | 13/13 | 7/13 | 7/13 | 7/7 |
| multiple errors | 5/5 | 0/5 | 0/5 | 0/2 |
| type mismatch | 6/6 | 0/6 | 0/6 | N/A (0 eligible) |
| unsupported minic | N/A (0 eligible) | N/A (0 eligible) | N/A (0 eligible) | N/A (0 eligible) |
| valid control | N/A (0 eligible) | N/A (0 eligible) | N/A (0 eligible) | N/A (0 eligible) |
| valid syntax wrong logic | 0/4 | 0/4 | 0/4 | N/A (0 eligible) |
| variable declaration | 1/1 | 1/1 | 1/1 | 1/1 |
| wrong function argument | 5/6 | 0/6 | 0/6 | N/A (0 eligible) |
| wrong variable reference | 3/5 | 0/5 | 0/5 | N/A (0 eligible) |

## Hybrid

| Metric | Result |
|---|---:|
| detection precision | 77/77 |
| detection recall | 77/95 |
| compiler fault detection recall | 77/77 |
| classification accuracy | 20/28 |
| exact correction match | 24/88 |
| top 1 repair accuracy | 25/88 |
| top 3 repair accuracy | 25/88 |
| compiler valid repair rate | 33/42 |
| intention recovery accuracy | 25/88 |
| incorrect repair rate | 2/27 |
| unknown intent rate | 61/88 |
| behavioral test success | N/A (0 eligible) |
| automatic repair rate | 11/95 |
| automatic edit count | 11/104 |
| automatic abstention rate | 84/95 |
| approval required rate | 26/95 |
| workbench correct proposals | 28/88 |
| unsafe provider rejection rate | 0/95 |
| unapplied safety review rate | 26/95 |
| ambiguous case abstention rate | 7/7 |
| automatic intended repair rate | 10/88 |
| regression count | 0/9 |
| average correction latency ms | 5.13 ms (285 samples) |
| p95 correction latency ms | 12.79 ms (285 samples) |

| Split | Detection recall | Top 1 | Top 3 | Approval required |
|---|---:|---:|---:|---:|
| evaluation | 20/28 | 10/26 | 10/26 | 7/28 |
| phase_1_5_holdout | 57/67 | 15/62 | 15/62 | 19/67 |

| Category | Detection recall | Top 1 | Top 3 | Compiler valid |
|---|---:|---:|---:|---:|
| ambiguous intent | 7/7 | N/A (0 eligible) | N/A (0 eligible) | 5/7 |
| array indexing | 4/6 | 1/6 | 1/6 | 1/2 |
| array indexing or declaration | 2/2 | 1/2 | 1/2 | 1/1 |
| incorrect arithmetic | 1/2 | 0/2 | 0/2 | 1/1 |
| incorrect comparison | 0/1 | 0/1 | 0/1 | N/A (0 eligible) |
| incorrect condition | 3/5 | 0/5 | 0/5 | N/A (0 eligible) |
| incorrect conditional | 0/1 | 0/1 | 0/1 | N/A (0 eligible) |
| incorrect delimiter | 5/5 | 3/5 | 3/5 | 3/3 |
| incorrect operator | 6/8 | 4/8 | 4/8 | 4/4 |
| incorrect return | 3/4 | 0/4 | 0/4 | 2/2 |
| incorrect variable reference | 4/5 | 0/5 | 0/5 | N/A (0 eligible) |
| invalid declaration | 6/6 | 1/6 | 1/6 | 1/2 |
| missing or incorrect return | 1/1 | 0/1 | 0/1 | N/A (0 eligible) |
| missing or mismatched brackets | 2/2 | 2/2 | 2/2 | 2/2 |
| missing semicolon | 13/13 | 11/13 | 11/13 | 11/11 |
| multiple errors | 5/5 | 0/5 | 0/5 | 0/4 |
| type mismatch | 6/6 | 0/6 | 0/6 | N/A (0 eligible) |
| unsupported minic | N/A (0 eligible) | N/A (0 eligible) | N/A (0 eligible) | N/A (0 eligible) |
| valid control | N/A (0 eligible) | N/A (0 eligible) | N/A (0 eligible) | N/A (0 eligible) |
| valid syntax wrong logic | 0/4 | 0/4 | 0/4 | N/A (0 eligible) |
| variable declaration | 1/1 | 1/1 | 1/1 | 1/1 |
| wrong function argument | 5/6 | 1/6 | 1/6 | 1/2 |
| wrong variable reference | 3/5 | 0/5 | 0/5 | N/A (0 eligible) |

## Ollama Assisted

Skipped by request
