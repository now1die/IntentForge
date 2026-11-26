# Family admission

The audit compared source and reference programs against 1,346 historical sources using normalized source, alpha-renamed shape and near-match similarity. It also compared specifications, test sets, upstream revision IDs and cross-partition edit shapes. Fault/control pairs stay together. The frozen file contained 16 final, two development and two selection programs. [Audit output](../benchmarks/reports/phase13-audit-v1.json)

| Excluded family | Evidence |
| --- | --- |
| bucket-order | Reference near-match to historical program, similarity 0.96 |
| sum-exclusive | Historical normalized shape and upstream revision reuse |
| development-double | Historical normalized shape |
| selection-cube | Historical normalized shape |

Twelve final programs remained. The development and selection partitions have zero admitted programs after quarantine. No estimates of selection accuracy or effective independent tuning are available. No cross-partition overlaps or shared cross-partition edit shapes were reported. Similarity screening cannot establish conceptual independence. Historical search cases appear only in a separately labeled diagnostic replay.
