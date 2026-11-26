# Discovery and fresh execution

Each admitted family reserves the last three frozen inputs for holdout. The audit checks that their argument tuples are absent from discovery. Synthesis receives discovery expectations. The live evaluator then submits each returned program with the held-out vectors using verification-only requests to the private worker. See the per-candidate edit, exact flag, status, steps and counterexample array in the [live report](../benchmarks/reports/phase13-live-v1.json).

All three recommended changes passed their three fresh vectors. No holdout counterexample to a recommended change was observed. The independent unit of generalization is the defect family. Repeating related inputs does not enlarge that count.

| Held-out input | Original observation | Expected |
| --- | ---: | ---: |
| Maximum, length 0 and cells 52, −6, 7 | −98 | −99 |
| TimSort, length 0 and cells −15, 29 | −81 | −82 |
| Digit count, −3 | 0 | 1 |
| Combination count, n = −5 and k = 2 | 0 | −73 |
| Green channel, nibbles 2, 5, 15, 0, 3, 11 | 3 | 240 |

Agreement on these vectors does not establish correctness outside the recorded domains. The first two cases received repairs. The last three remained detected without a recommendation.
