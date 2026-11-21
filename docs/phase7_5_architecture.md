# Phase 7.5 architecture

Public profile 75 extends the existing Phase 7 engine. The compiler, CFG, reaching definitions, path feasibility and interprocedural global-effect summaries provide the analysis inputs. The new layer builds guarded-return and scalar-helper witnesses and proposes small source-span edits. Existing compiler validation, deduplication and deterministic ranking handle the resulting candidates.

The static API reports source-located progress evidence and unresolved shapes. The behavioral gateway sends the original and at most four alternatives to private worker version 7. It classifies original observations after validating snapshot, entry, candidate and test identity. Earlier profiles retain their default behavior and API response shapes.
