# Sources and freeze

Seven defect/correction pairs were pinned from TheAlgorithms/Python (MIT) and TheAlgorithms/JavaScript (GPL-3.0). Both repositories belong to the same organization. The archive includes the upstream path, both full Git commit IDs, original source snapshots and license copies. SHA-256 digests cover the snapshots, license files, revision index and frozen case file. Each case describes its scalar observation and input restrictions. [Revision index](../benchmarks/phase13_data/revisions.json) · [Hash manifest](../benchmarks/phase13_data/manifest-v1.json) · [Case definitions](../benchmarks/phase13_fixtures.py)

The final freeze commit was `4758ec2`, before final scoring. The cases file digest is `ec88331bc43de6f5bfa90d1009116cdb124ede114633ba6f4a54c29fc84bdb0b`. The second freeze added two pinned JavaScript families after a candidate family was quarantined. The audit is applied to the full frozen file.

Expected outputs come from separate small domain functions such as decimal digit length, binomial count, sorted first element, maximum and a green-channel calculation. Replay executes both pinned revisions in their original language and compares the observations to the corresponding Mini-C adapter on every discovery and holdout input. Error sentinels and finite scalar projections are part of these contracts. [Replay observations](../benchmarks/reports/phase13-upstream-v1.json)

`INDEPENDENT_HUMAN_REVIEW=NOT_AVAILABLE`. Upstream commits document the fixes independently of IntentForge. The adaptation, expectations and evaluation were prepared in this project.
