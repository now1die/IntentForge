# Historical external failure taxonomy

All six Phase 7 cases had zero guided candidates and no exact rank. Their existing compiler and program evidence could describe source structure, while the numerical test observations came from the restricted worker. Each fault and exact reference is available with its source offset and archived attempt count in the [static report](../benchmarks/reports/phase75-static-v1.json).

| Historical family | Fault site and exact reference | Miss and verified original |
| --- | --- | --- |
| Josephus ring | Self-call kept `people`. The reference decrements it by one. | Candidate generation excluded the remainder expression enclosing the recursion. The worker reached call depth. |
| Digital root | Quotient used `/9`. The reference uses `/10`. | Missing relationship between quotient and remainder on the same lexical binding. The original mismatched. |
| Automorphic suffix | Temporary used `/=100`. The reference uses `/=10`. | Missing relationship between the scale update, loop threshold and quotient. The original mismatched. |
| Polygonal layer | Coefficient used `sides-3`. The reference uses `sides-4`. | The closed-form coefficient was outside candidate generation from examples. The original mismatched. |
| Manhattan grid | Both gap calls used `a` in the first slot. The second should use `b`. | Missing helper argument reasoning and no archived test pair varying only the omitted input. The original mismatched. |
| Arithmetic list | Formula used `count*difference`. The reference uses `(count-1)*difference`. | Nonrecursive predecessor factor was outside bounded synthesis. The original mismatched. |

Phase 7.5 recovered the exact Josephus, digital-root and automorphic changes on their archived examples. The three other historical misses remain. Those results diagnose repair mechanisms. External generalization is measured on the separate six-family Phase 7.5 cohort.
