# Range origins

The new index-origin repair ties an affine index expression to the invariant lexical origin used to initialize its enclosing traversal. A collection scan may compute that origin before the traversal. The checked model follows the definition and validates every sampled cell read. In the new minimum-grid fixture the traversal begins at the scanned minimum and the corrected index subtracts that same minimum.

The archived missing-member implementation needs a missing bounds scan and a data-dependent XOR helper. That combination exceeds the current proof and remains unrecovered.
