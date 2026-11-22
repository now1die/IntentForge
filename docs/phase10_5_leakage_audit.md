# Leakage audit

The corpus was committed before final evaluation. The audit covers exact source, alpha-normalized token shape, near duplicates, reused references and metadata, prior bug-fix SHAs and family/repository partitions. It checked 1,271 historical sources. All final cases were admitted. One generic edit shape recurred across partitions and is recorded.

All four archived diagnostics stay out of the final evaluation. The new Python first-match fix and the archived Java saturated lower bound are distinct defects, with different upstream commits, interfaces, normalizations and repair targets. [Leakage report](../benchmarks/reports/phase105-audit-v1.json)
