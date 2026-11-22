# Cyclic-array reasoning

The model counts cyclic descents, including the last-to-first seam, in the complete observed cells used by a fixed-extent pivot loop. It records duplicate cells and whether an equal comparison was observed. Candidate generation requires at most one cyclic descent per supplied case and independently supplied minimum-position outputs. It preserves the original ordered branches and inserts a one-step equal-endpoint refinement in the admitted binary pivot form. The full edit must satisfy every sampled output and make consistent progress.

This phase tests two-cell and singleton logical-prefix controls, unrotated and all-equal inputs, duplicated nonminimum cells and multiple rotations. A variable logical extent beyond the tested controls and the archived three-way neighbor search remain unsupported. A candidate can be rejected when ties among minima encode a different positional contract.
