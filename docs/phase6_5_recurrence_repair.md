# Recurrence repair

`RECURRENCE_OPERATOR_MISMATCH` compares bounded one-token alternatives among addition, subtraction and multiplication. It requires two direct recursive operands with distinct small offsets toward a literal guard and at least one type-compatible supplied input outside the initial base domain. Code-only evidence describes the existing recurrence, including expressions with weighted or nonrecursive terms. Supplied expectations go to the restricted worker.

Subtraction, multiplication, weighting and asymmetry can all express intentional recurrences. Static analysis may propose alternatives for a correct source given examples. The alternatives require manual review and the worker exposes multiple passing candidates when the examples underdetermine the operator. Coefficient, omitted-term, nonlinear and helper-mediated synthesis remain unsupported.
