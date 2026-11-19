# Phase 2 frozen evaluation

Ranker: `intention-v1-logistic`.
Behavioral runtime observations: 0.

## Historical (111 cases)

| Configuration | Top 1 | Top 3 | Candidate recall | Rank success given candidate | Valid top | Mean / p95 ms |
|---|---:|---:|---:|---:|---:|---:|
| rules | 24/88 | 24/88 | 24/88 | 24/24 | 32/42 | 4.78 / 14.62 |
| original ml | 18/88 | 18/88 | 18/88 | 18/18 | 20/22 | 4.33 / 11.67 |
| original hybrid | 25/88 | 25/88 | 25/88 | 25/25 | 33/42 | 5.21 / 12.62 |
| context deterministic | 37/88 | 38/88 | 38/88 | 37/38 | 51/52 | 3.32 / 9.76 |
| context learned | 36/88 | 38/88 | 38/88 | 36/38 | 51/52 | 3.29 / 9.50 |
| full intention | 36/88 | 38/88 | 38/88 | 36/38 | 51/52 | 3.34 / 9.99 |

## Final (32 cases)

| Configuration | Top 1 | Top 3 | Candidate recall | Rank success given candidate | Valid top | Mean / p95 ms |
|---|---:|---:|---:|---:|---:|---:|
| rules | 2/19 | 2/19 | 2/19 | 2/2 | 2/3 | 2.82 / 5.60 |
| original ml | 0/19 | 0/19 | 0/19 | 0/0 | 0/0 | 3.10 / 4.91 |
| original hybrid | 0/19 | 0/19 | 0/19 | 0/0 | 0/1 | 3.29 / 7.32 |
| context deterministic | 5/19 | 9/19 | 9/19 | 5/9 | 12/12 | 2.37 / 6.36 |
| context learned | 6/19 | 9/19 | 9/19 | 6/9 | 12/12 | 2.51 / 6.48 |
| full intention | 16/19 | 19/19 | 19/19 | 16/19 | 21/21 | 4.38 / 10.85 |
