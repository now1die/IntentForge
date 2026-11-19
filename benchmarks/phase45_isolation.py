"""Benchmark the real verified local worker through the main API gateway."""
import argparse
from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path
from time import perf_counter

from fastapi.testclient import TestClient

from ai.correction_safety import repair_key
from backend.app.main import app
from benchmarks.phase45_vm import summary

URL = "/v1/behavioral-verification"
CASES = (
    ("triple-adjust", "int f(int x){return x+1;}", [4], 11, "x*3-1",
     "int f(int x){return x*3-1;}"),
    ("descending-buffer", "int buf[5];int f(){int s=0;for(int j=3;j>=-1;j--){buf[j]=j+1;s+=buf[j];}return s;}",
     [], 10, None, "int buf[5];int f(){int s=0;for(int j=3;j>-1;j--){buf[j]=j+1;s+=buf[j];}return s;}"),
    ("coincident-endpoints", "int f(int bottom,int top){return missing;}", [9, 9], 9, None,
     "int f(int bottom,int top){return bottom;}"),
    ("runtime-rejection", "int f(int x){return x+1;}", [8], 9, "x/(x-x)", None),
    ("valid-latch", "bool f(bool x){return !x;}", [False], True, None, None),
    ("unavailable-float", "int f(){float n=3.0;return 5;}", [], 5, None, None),
)


def evaluate():
    rows = []
    durations = []
    with TestClient(app, base_url="http://127.0.0.1:8000", client=("127.0.0.1", 54000)) as client:
        assert client.get(URL + "/capability").json()["status"] == "available"
        for family, source, args, expected, expression, reference in CASES:
            request = {"source": source, "entry_point": "f", "compare_candidates": True, "trace": True,
                       "return_expression": expression, "vectors": [{"arguments": args, "expected": expected}]}
            started = perf_counter()
            outcome = client.post(URL, json=request).json()
            durations.append((perf_counter()-started)*1000)
            assert outcome["availability"]["status"] == "available", outcome
            target = repair_key(reference) if reference else None
            candidates = outcome["candidates"]
            ref = next((c["static_rank"] for c in candidates if repair_key(c["source"]) == target), None)
            rows.append({"family": family, "labeled_reference": reference is not None, "reference_static_rank": ref,
                         "original_status": outcome["original"]["status"], "compiler_valid_candidates": len(candidates),
                         "executable_candidates": sum(row["behavior"]["status"] != "EXECUTION_UNSUPPORTED" for row in candidates),
                         "passing": sum(row["behavior"]["status"] == "MATCHES_SUPPLIED_TESTS" for row in candidates),
                         "runtime_failure": sum(row["behavior"]["status"] == "BEHAVIOR_UNKNOWN" for row in candidates),
                         "multiple_matches": outcome["comparison_status"] == "MULTIPLE_MATCHES",
                         "disagreements": sum(probe["relation"] == "disagree" for probe in outcome["probes"]),
                         "requires_approval": outcome["requires_approval"]})
        assert all(row["requires_approval"] for row in rows)
        assert any(row["multiple_matches"] and row["disagreements"] for row in rows)
        assert any(row["runtime_failure"] for row in rows)
        payload = {"source": "int f(){for(;;);}", "entry_point": "f",
                   "vectors": [{"arguments": [], "expected": 0}], "limits": {"steps": 15_000}}
        with ThreadPoolExecutor(max_workers=8) as workers:
            concurrent = list(workers.map(lambda _: client.post(URL, json=payload).json(), range(8)))
        outcomes = [item["availability"]["status"] for item in concurrent]
        assert set(outcomes) <= {"available", "capacity_reached"} and "available" in outcomes
        assert all(item["original"]["status"] == "EXECUTION_LIMITED"
                   for item in concurrent if item["availability"]["status"] == "available")
        assert client.get(URL + "/capability").json()["status"] == "available"
    return {"version": 1, "provenance": "Real private Mini-C worker through the loopback gateway",
            "repair_families": rows, "comparison_ms": summary(durations),
            "eight_concurrent_requests": {key: outcomes.count(key) for key in sorted(set(outcomes))}}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()
    payload = json.dumps(evaluate(), indent=2) + "\n"
    if args.out:
        args.out.write_text(payload)
    print(payload, end="")
