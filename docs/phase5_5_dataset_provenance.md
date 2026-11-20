# Phase 5.5 dataset provenance

The frozen manifest contains 63 records across 34 source families. Before quarantine, the partitions contain 2 training, 8 development, 4 selection, 2 calibration and 47 final records. The audit admitted 52 records, including 40 final cases across 21 families. The admitted final cases contain 19 faults, 19 controls and 2 partial specifications. The preferred corpus size was 40 faults, 40 controls and 10 ambiguous cases.

The external-adaptation group contains 22 records across 11 algorithm families. The source implementations came from TheAlgorithms/Python at `30507bbe41397065728167fb09aa820f9fce8dc7`, under MIT. The fixture author manually ported bounded scalar tasks and introduced controlled faults. These are external algorithm adaptations with project-authored faults and checks. No outside reviewer adjudicated the Phase 5.5 labels. The internal fixtures have no separate published reuse license.

The author checked references against independent calculations or documented sequence terms. The benchmark confirms that each reference or control matches those fixed vectors and each adjudicable faulty input fails at least one. Ambiguous cases assert only the supplied observations. The study never derives an expected value from an IntentForge candidate.

To reproduce the fixture bytes, download the exact upstream files listed in the manifest from its pinned revision into one directory using the original file basenames. Run `python -m benchmarks.phase55_fixtures /path/to/upstream-files` in a disposable checkout. The output hashes must match the committed manifest. Normal evaluation reads the frozen files without network access.

[Frozen cases](../benchmarks/data/phase55/cases-v1.json) · [Manifest and source hashes](../benchmarks/data/phase55/manifest-v1.json) · [Upstream license](../benchmarks/data/phase55/TheAlgorithms-MIT.md)
