# Phase 3.5 baseline

The fetched base is `92441c1f0af60f6eb9d599918935f580aed20f3e`.
The head commits of PR #4 and PR #5 are ancestors of this merge.
This baseline ran before code changes in the new worktree.

- Python 546 passed, including 14 dedicated Clang tests, with libclang 19.1.7 enabled.
- The production frontend build and 21 Chromium tests passed.
- The compiler suite passed 220 cases. The keyboard and array report reproduced
  65 cases with 45 withheld references still visible and zero unexpected outcomes.
- The stress suite checked 3,758 inputs with zero crashes. Historical corpus,
  training and benchmark checks for Phase 1, Phase 2, Phase 2.5 and ML v3 passed.
- The Clang benchmark passed 12 API requests with 13 translation units.

Mini-C v3 matched 6/18 held-out top-1 repairs and generated 9/18. The
learned methods did not qualify for activation. The two compiler routes
used distinct evidence layouts. Clang was optional and locally isolated;
public deployment had not been verified. No local Ollama executable or
listening service was detected. Behavioral outcomes were unavailable.
