# Phase 6 baseline

The repository default is `phase-1-intention-benchmarking`. Phase 5 PR #9 and Phase 5.5 PR #10 are merged. The latest default-branch commit at verification was `2525e91187099f909319eab3f7dcf4e1e40a5be8`. This branch starts at that revision and targets the default branch directly.

All five post-merge workflows passed. Python, Clang analysis, Frontend tests, Benchmark validation and Isolated Mini-C execution completed successfully. The optional Ollama job was skipped. No required post-merge job failed, was pending or was unavailable.

The local baseline passed 680 Python tests and 28 Chromium tests. The default-disabled local profile skipped two worker-dependent Python cases and five live browser cases. The production frontend built. Historical corpus, ML, VM and Clang checks reproduced, 220 compiler cases passed, the 65 keyboard and array cases had zero unexpected results, and all 3,758 stress fixtures ran.

The preserved Phase 5.5 report recorded 2/19 exact reference recall, 0/11 on external-adaptation faults, and one comparison-orientation miss. Those are historical results. Phase 6 uses a separately frozen cohort.

[Post-merge CI](https://github.com/now1die/IntentForge/actions/runs/44810178379) · [Historical Phase 5.5 review](PHASE_5_5_FINAL_REVIEW.md)
