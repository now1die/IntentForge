# Semantic state

`analysis_evidence.semantic_state` runs a worklist over the existing statement-level CFG. A slot is a lexical binding and an optional literal cell index. State contains the subset definitely initialized, the subset possibly initialized, typed literal constraints, and guaranteed comparisons on incoming edges. At a join, definite facts and path facts intersect while possible initialization unions. Writes invalidate value and path constraints. Function parameters begin initialized independently of their value.

The pass uses the existing 1,800-transfer ceiling per function and shared program deadline. It tracks fixed local arrays up to 32 cells and emits at most 48 evidence rows. A partially converged state yields an analysis-limit status. Facts include function, binding, source span and CFG site. Reaching CFG definition sites are included where available. Logical and coordinate observations are attached separately to the static facts that prompted them.
