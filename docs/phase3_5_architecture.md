# Phase 3.5 architecture

The workstreams share the merged Phase 3 base and have dedicated tests in
`tests/test_phase35_workstreams.py`. Browser tests exercise the real
compiler adapters, editor snapshots and reviewed repair presentation.

- **A** Mini-C v4 adds a counted-loop generator before existing v3
  hypotheses, under the existing candidate and time budgets. It validates and
  deduplicates every proposal. The new ranker artifact is independently versioned.
- **B** `analysis_evidence` normalizes native compiler evidence. The
  versioned endpoint selects one provider by the requested language. Existing
  C and Mini-C routes continue to expose their own representations.
- **C** The Clang worker remains isolated and opt-in. The transport and readiness
  checks enforce resource limits, and model loading verifies packaged bytes.
- **D** The opt-in v4 workbench shows evidence-based review guidance and
  abstains when evidence is weak or alternatives are ambiguous.
- **E** Ollama handles bounded advisory requests on the correction path.
  The compiler and intention paths operate offline.
- **F** A typed behavioral contract accepts evidence from a future trusted
  executor, bound to source and test vectors. This release has no executor.

For C, the flow is editor or API → bounded validated request → isolated
libclang worker → typed evidence. For Mini-C, the flow is
PLY AST and semantic context → bounded hypotheses → compiler validation →
optional category-gated ranking → human review. Evidence inspection
and behavioral verification are separate interfaces.
