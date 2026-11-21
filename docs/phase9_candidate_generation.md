# Candidate generation

Phase 9 uses trusted scalar expectations and the shared bounded search and
compiler validation. It preserves Phase 8 typed domains, partial inputs,
earlier engine profiles and deterministic ranking. Partial observations never
supply missing expected values.

Finite coverage includes the samples and paths named in the evidence. A
candidate ID and each edit refer to the original source snapshot. All edits
in a multi-site proposal are reviewed together. After compiler validation,
the isolated verifier compares observed values with trusted expectations.
