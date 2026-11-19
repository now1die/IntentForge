# Phase 1 benchmark

32 frozen cases, corpus v1, seed 42.

- ML-only top-1 matches missed by rule-based correction: seed-declaration, seed-indexing.
- Rule-based top-1 matches missed by ML-only correction: seed-ambiguous-condition, seed-interleaved-declaration-semicolon.
- Hybrid top-1 matches missed by ML-only correction: seed-ambiguous-condition.
- 8 valid Mini-C cases contained specification-level logic errors. General intent detection is unsupported.
- Behavioral equivalence was not executed. A compiler-valid proposal can still change behavior.

## Rule Based

| Metric | Result |
|---|---:|
| detection precision | 20/20 |
| detection recall | 20/28 |
| compiler fault detection recall | 20/20 |
| classification accuracy | N/A (0 eligible) |
| exact correction match | 9/26 |
| top 1 repair accuracy | 9/26 |
| top 3 repair accuracy | 9/26 |
| compiler valid repair rate | 12/12 |
| intention recovery accuracy | 9/26 |
| incorrect repair rate | 1/10 |
| behavioral equivalence verified | 0/12 |
| ambiguous case abstention rate | 2/2 |
| automatic intended repair rate | 7/26 |
| regression count | 0/3 |
| average correction latency ms | 3.63 ms (84 samples) |
| p95 correction latency ms | 9.93 ms (84 samples) |

| Category | Detection recall | Top 1 | Top 3 | Compiler valid |
|---|---:|---:|---:|---:|
| ambiguous intent | 2/2 | N/A (0 eligible) | N/A (0 eligible) | 2/2 |
| array indexing or declaration | 2/2 | 0/2 | 0/2 | N/A (0 eligible) |
| incorrect arithmetic | 1/2 | 0/2 | 0/2 | 1/1 |
| incorrect comparison | 0/1 | 0/1 | 0/1 | N/A (0 eligible) |
| incorrect conditional | 0/1 | 0/1 | 0/1 | N/A (0 eligible) |
| incorrect operator | 2/2 | 2/2 | 2/2 | 2/2 |
| incorrect variable reference | 4/5 | 0/5 | 0/5 | N/A (0 eligible) |
| missing or incorrect return | 1/1 | 0/1 | 0/1 | N/A (0 eligible) |
| missing or mismatched brackets | 2/2 | 2/2 | 2/2 | 2/2 |
| missing semicolon | 5/5 | 5/5 | 5/5 | 5/5 |
| unsupported minic | N/A (0 eligible) | N/A (0 eligible) | N/A (0 eligible) | N/A (0 eligible) |
| valid control | N/A (0 eligible) | N/A (0 eligible) | N/A (0 eligible) | N/A (0 eligible) |
| valid syntax wrong logic | 0/4 | 0/4 | 0/4 | N/A (0 eligible) |
| variable declaration | 1/1 | 0/1 | 0/1 | N/A (0 eligible) |

## Existing Ml

| Metric | Result |
|---|---:|
| detection precision | 20/20 |
| detection recall | 20/28 |
| compiler fault detection recall | 20/20 |
| classification accuracy | 11/11 |
| exact correction match | 10/26 |
| top 1 repair accuracy | 10/26 |
| top 3 repair accuracy | 10/26 |
| compiler valid repair rate | 10/10 |
| intention recovery accuracy | 10/26 |
| incorrect repair rate | 0/10 |
| behavioral equivalence verified | 0/10 |
| ambiguous case abstention rate | 2/2 |
| automatic intended repair rate | 3/26 |
| regression count | 0/3 |
| average correction latency ms | 3.42 ms (84 samples) |
| p95 correction latency ms | 4.64 ms (84 samples) |

| Category | Detection recall | Top 1 | Top 3 | Compiler valid |
|---|---:|---:|---:|---:|
| ambiguous intent | 2/2 | N/A (0 eligible) | N/A (0 eligible) | N/A (0 eligible) |
| array indexing or declaration | 2/2 | 1/2 | 1/2 | 1/1 |
| incorrect arithmetic | 1/2 | 0/2 | 0/2 | N/A (0 eligible) |
| incorrect comparison | 0/1 | 0/1 | 0/1 | N/A (0 eligible) |
| incorrect conditional | 0/1 | 0/1 | 0/1 | N/A (0 eligible) |
| incorrect operator | 2/2 | 2/2 | 2/2 | 2/2 |
| incorrect variable reference | 4/5 | 0/5 | 0/5 | N/A (0 eligible) |
| missing or incorrect return | 1/1 | 0/1 | 0/1 | N/A (0 eligible) |
| missing or mismatched brackets | 2/2 | 2/2 | 2/2 | 2/2 |
| missing semicolon | 5/5 | 4/5 | 4/5 | 4/4 |
| unsupported minic | N/A (0 eligible) | N/A (0 eligible) | N/A (0 eligible) | N/A (0 eligible) |
| valid control | N/A (0 eligible) | N/A (0 eligible) | N/A (0 eligible) | N/A (0 eligible) |
| valid syntax wrong logic | 0/4 | 0/4 | 0/4 | N/A (0 eligible) |
| variable declaration | 1/1 | 1/1 | 1/1 | 1/1 |

## Hybrid

| Metric | Result |
|---|---:|
| detection precision | 20/20 |
| detection recall | 20/28 |
| compiler fault detection recall | 20/20 |
| classification accuracy | 11/11 |
| exact correction match | 10/26 |
| top 1 repair accuracy | 10/26 |
| top 3 repair accuracy | 10/26 |
| compiler valid repair rate | 13/13 |
| intention recovery accuracy | 10/26 |
| incorrect repair rate | 1/11 |
| behavioral equivalence verified | 0/13 |
| ambiguous case abstention rate | 2/2 |
| automatic intended repair rate | 3/26 |
| regression count | 0/3 |
| average correction latency ms | 4.19 ms (84 samples) |
| p95 correction latency ms | 10.72 ms (84 samples) |

| Category | Detection recall | Top 1 | Top 3 | Compiler valid |
|---|---:|---:|---:|---:|
| ambiguous intent | 2/2 | N/A (0 eligible) | N/A (0 eligible) | 2/2 |
| array indexing or declaration | 2/2 | 1/2 | 1/2 | 1/1 |
| incorrect arithmetic | 1/2 | 0/2 | 0/2 | 1/1 |
| incorrect comparison | 0/1 | 0/1 | 0/1 | N/A (0 eligible) |
| incorrect conditional | 0/1 | 0/1 | 0/1 | N/A (0 eligible) |
| incorrect operator | 2/2 | 2/2 | 2/2 | 2/2 |
| incorrect variable reference | 4/5 | 0/5 | 0/5 | N/A (0 eligible) |
| missing or incorrect return | 1/1 | 0/1 | 0/1 | N/A (0 eligible) |
| missing or mismatched brackets | 2/2 | 2/2 | 2/2 | 2/2 |
| missing semicolon | 5/5 | 4/5 | 4/5 | 4/4 |
| unsupported minic | N/A (0 eligible) | N/A (0 eligible) | N/A (0 eligible) | N/A (0 eligible) |
| valid control | N/A (0 eligible) | N/A (0 eligible) | N/A (0 eligible) | N/A (0 eligible) |
| valid syntax wrong logic | 0/4 | 0/4 | 0/4 | N/A (0 eligible) |
| variable declaration | 1/1 | 1/1 | 1/1 | 1/1 |

## Ollama Assisted

Ollama is unavailable at http://127.0.0.1:11434 or model 'llama3.2:3b' is not installed
