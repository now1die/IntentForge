# Phase 5 architecture

Choose engine version 5 on the existing intention endpoint or workbench. The static engine uses the compiler's AST, ordered source spans and symbol table to track lexical bindings and direct writes. Its hypotheses feed the existing edit application, compiler validation, structural deduplication and deterministic ranking. The structural scan also returns located evidence independently of the candidate pool. Earlier engine versions use their existing paths.

Interactive comparison accepts engine version 5 through the Phase 4.5 loopback gateway. It sends one source plus at most four server-generated compiler-valid alternatives across the owner-only Unix socket. The worker verifies supplied examples and evaluates observational probes in one disposable child. The gateway retains static rank, reports a separate behavioral review order and checks identity before attaching evidence. The workbench requires explicit approval on the source snapshot that was reviewed.

[Static reasoning](phase5_code_only_analysis.md) · [Isolated behavior](phase5_behavior_guided_ranking.md) · [Security](phase5_security.md)
