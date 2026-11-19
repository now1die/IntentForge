# Phase 2 architecture

The implementation starts from `4923db21ffdaef3d7c15b6712ceba7b1fec047ba`,
the merge of Phase 1.5 pull request #1 into `phase-1-intention-benchmarking`.

The Phase 2 entry point analyzes source independently of automatic correction.
It indexes the existing Mini-C AST, compiler diagnostics, inferred types, and
scopes. Malformed input retains tokens and compiler diagnostics. It receives no
inferred semantic tree. Optional user requirements are expressed as scoped
return or condition expressions, plain-language requirements, or finite examples.
Structured requirements specify the shape of an expression. They do not prove
the behavior of the whole program.

Bounded generators propose local edits from visible symbols, types, signatures,
and requirements. Each candidate is explained and rechecked by the existing
lexical, syntax, and semantic pipeline. Speculative edits are review-only.
The existing correction endpoints and safety policy continue to govern existing
workflows.

The ranking experiment compares a deterministic order and a small pointwise
scikit-learn model. Training and model selection use separate program families
and do not use frozen Phase 1 corpora. A failing validation comparison keeps
the deterministic order in the application. Scores, when available, are
relative ranking values. Runtime execution and behavioral equivalence remain
outside this architecture.
