# External validation

Run `python -m benchmarks.phase12_upstream --check` with Python 3.12 and Node 24. The script validates the archive hashes and runs each reviewed revision in a temporary process with an empty environment and an eight-second timeout. It uses Python isolated mode and Node file read permissions. These are offline, pinned specimens outside the web API. The Node driver omits the archived top-level demo. The Python import leaves its interactive main block dormant.

All 16 declared inputs matched their adaptations before and after the external fixes, for 32 paired outcomes. [Pinned replay report](../benchmarks/reports/phase12-upstream-v1.json)
