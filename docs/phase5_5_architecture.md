# Phase 5.5 architecture

Version 55 is an opt-in extension of the existing intention API. The engine runs the bounded Phase 5 scan and partitions its hypotheses into accepted and withheld findings. Withheld findings carry the original signal and a located reason. Accepted proposals use the existing edit validator and deterministic ranker. Earlier engine versions keep their behavior, including their older fallback hypotheses.

The live gateway uses version 55 for static generation and sends the unchanged version 5 protocol to the isolated worker. The worker receives compiler-valid alternatives chosen by the server. The gateway attaches results after verifying the program fingerprint, candidate IDs, entry point and typed vectors. Static order, observed order, ambiguity and explicit source approval remain separate.

[Security boundary](phase5_5_security.md) · [Workbench](phase5_5_workbench.md)
