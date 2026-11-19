# Phase 2.5 evaluation

Reference matches and compiler validity are static observations.

## Historical (111 cases)

| Mode | Recall | Top 1 | Top 3 | Logic precision / recall | Mean / p95 ms |
|---|---:|---:|---:|---:|---:|
| rules | 24/88 | 24/88 | 24/88 | 0/0 / 0/18 | 4.51 / 11.92 |
| original_ml | 18/88 | 18/88 | 18/88 | 0/0 / 0/18 | 4.35 / 12.51 |
| original_hybrid | 25/88 | 25/88 | 25/88 | 0/0 / 0/18 | 5.12 / 12.78 |
| phase2_deterministic | 38/88 | 37/88 | 38/88 | 2/2 / 2/18 | 3.66 / 13.70 |
| phase2_learned | 38/88 | 36/88 | 38/88 | 2/2 / 2/18 | 3.33 / 9.54 |
| expanded_deterministic | 40/88 | 39/88 | 40/88 | 2/2 / 2/18 | 3.38 / 10.44 |
| expanded_learned | 40/88 | 37/88 | 40/88 | 2/2 / 2/18 | 3.41 / 10.83 |
| full_code_only | 40/88 | 37/88 | 40/88 | 2/2 / 2/18 | 3.41 / 10.83 |

## Evaluation (44 cases)

| Mode | Recall | Top 1 | Top 3 | Logic precision / recall | Mean / p95 ms |
|---|---:|---:|---:|---:|---:|
| rules | 1/30 | 1/30 | 1/30 | 0/0 / 0/18 | 3.58 / 6.65 |
| original_ml | 1/30 | 1/30 | 1/30 | 0/0 / 0/18 | 3.74 / 6.59 |
| original_hybrid | 1/30 | 1/30 | 1/30 | 0/0 / 0/18 | 4.01 / 7.64 |
| phase2_deterministic | 11/30 | 8/30 | 11/30 | 0/0 / 0/18 | 3.52 / 8.64 |
| phase2_learned | 11/30 | 8/30 | 11/30 | 0/0 / 0/18 | 3.66 / 10.16 |
| expanded_deterministic | 18/30 | 15/30 | 18/30 | 6/8 / 6/18 | 4.10 / 9.52 |
| expanded_learned | 18/30 | 16/30 | 18/30 | 6/8 / 6/18 | 4.16 / 9.62 |
| full_code_only | 18/30 | 16/30 | 18/30 | 6/8 / 6/18 | 4.16 / 9.62 |

## Matched Evidence Comparison (17 cases)

| Mode | Recall | Top 1 | Top 3 | Logic precision / recall | Mean / p95 ms |
|---|---:|---:|---:|---:|---:|
| full_code_only | 3/14 | 3/14 | 3/14 | 3/4 / 3/14 | 1.68 / 3.24 |
| full_natural_language | 7/14 | 7/14 | 7/14 | 9/9 / 9/14 | 4.15 / 8.84 |
| full_explicit | 14/14 | 14/14 | 14/14 | 14/14 / 14/14 | 7.19 / 42.71 |
