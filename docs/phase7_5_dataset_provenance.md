# Dataset provenance

The freeze includes 64 rows, including 58 frozen final rows. Six final algorithm families adapt MIT-licensed TheAlgorithms/Python code or documented algorithms at `30507bbe41397065728167fb09aa820f9fce8dc7`. The original bytes and hashes are pinned. Every injected bug is labeled project-authored. No external human reviewer participated.

Independent executable references compute digit conversion, recurrence values, modular sums, coprime counts and other expected behavior using separate formulas, Python operations or iteration. The evaluator verifies reference and control behavior before scoring. Redundant external cases were checked during the audit. Each adjudicable program has discovery and separate held-out inputs. Candidate generation and review can see discovery inputs only. The held-out inputs are sent afterward in separate verification-only worker requests.

[Corpus](../benchmarks/phase75_data/cases-v1.json) · [Manifest and license hashes](../benchmarks/phase75_data/manifest-v1.json)
