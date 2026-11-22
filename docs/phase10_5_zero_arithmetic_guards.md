# Checked zero-input arithmetic guards

The model records a checked division or remainder with zero divisor at a single source operation. It recognizes a direct entry parameter or at most two entry parameters passed into a projected pure denominator helper. Inserting a pure entry guard requires trusted constant expected results on the zero inputs, separate evidence for each admitted zero operand, and at least two successful nonzero inputs. A guard can return a typed nonzero sentinel.

Worker execution keeps the original division failure distinct from an output mismatch. A compatible alternative can appear in manual review when it passes the supplied tests. The existing recommendation policy requires confirmed mismatch evidence from the original before recommending a candidate. The archived LCM zero guard passes both suites. Divisors derived from arbitrary array expressions remain outside this candidate grammar.
