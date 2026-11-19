"""Measure actual per-child CPU/RSS and cold probe latency inside a local image."""
import json
import resource
from time import perf_counter

from execution_service.runner import run_worker

samples = []
for _ in range(5):
    before = resource.getrusage(resource.RUSAGE_CHILDREN)
    started = perf_counter()
    assert run_worker("probe") == {"boundary": "isolated-local-v1"}
    elapsed = (perf_counter() - started) * 1000
    after = resource.getrusage(resource.RUSAGE_CHILDREN)
    samples.append({"cold_probe_ms": round(elapsed, 3),
                    "child_cpu_ms": round((after.ru_utime + after.ru_stime - before.ru_utime - before.ru_stime) * 1000, 3),
                    "peak_child_rss_kib_so_far": after.ru_maxrss})
print(json.dumps({"version": 1, "container_scope": "Local disposable probe children", "samples": samples}, indent=2))
