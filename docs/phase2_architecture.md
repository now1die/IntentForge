# Phase 2 architecture

The implementation starts from `4923db21ffdaef3d7c15b6712ceba7b1fec047ba`,
the merge of Phase 1.5 pull request #1 into `phase-1-intention-benchmarking`.

The Phase 2 entry point analyzes source independently of automatic correction.
It indexes the existing Mini-C AST, compiler diagnostics, inferred types, and
scopes. Malformed input retains tokens and compiler diagnostics. It receives no
inferred semantic tree. Optional user requirements are expressed as scoped
return or condition expressions, plain-language requirements, or finite examples.
Structured requirements specify the shape of an expression. They supply structural evidence about the selected expression.

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

## Implemented data flow

1. `ai/intention_context.py` uses the existing lexer, parser, semantic analyzer,
   and symbol table. It indexes parent and child relationships, source spans,
   statement roles, scope, visible bindings, and expected and observed types.
   The partial path serializes tokens and diagnostics and marks missing context.
2. `ai/intention_requirements.py` locates a return or condition in one function.
   Its expression comparison preserves AST structure and ignores source spans.
   Input/output vectors and unsupported wording are recorded as requirements.
3. `ai/intention_candidates.py` proposes single edits and a few independent
   pairs. Visible declarations and function signatures supply alternatives.
   The requirement path supports known arithmetic, comparison, condition,
   variable, return, argument, and index changes.
4. `ai/intention_engine.py` validates proposed source through Mini-C, checks
   requirement matches again on the repaired AST, deduplicates token-equivalent
   proposals, and attaches factual evidence, candidate hypotheses, and review
   status. A candidate with remaining diagnostics can be inspected.
5. `ai/intention_ranker.py` loads the separately versioned model. Learned
   ordering is used only for comparable, scoped bindings in return-value
   positions. Compiler validity, requirement matches, and remaining diagnostics
   form the ordering strata before machine-learned scores are considered.
6. `POST /v1/intention-analysis` exposes the workflow. The React Intention tab
   shows structured findings, evidence, ranks, diffs, and explicit approval.
   The original Analyze and Correct actions and their response schemas remain
   available.

The analysis path bounds source characters, tokens, nesting, expression size,
and validation attempts. Its cooperative deadline stops candidate work between
compiler calls. Every intention edit remains review-only and every selectable
full repair has passed the compiler pipeline. Frontend approval is tied to the
source snapshot that produced the proposal. Runtime behavior remains unverified.
