"""Replay the reviewed pinned Python and JavaScript specimens in temporary processes."""
import argparse
import json
from pathlib import Path
from shutil import which
import subprocess
import sys
from tempfile import TemporaryDirectory

from ai.behavior_oracle import ExecutionLimits, Vector
from vm.behavioral_executor import MiniCOracle

from .phase6_evaluate import REPORTS
from .phase12_audit import audit
from .phase12_fixtures import EXTERNAL, ROOT

PYTHON_DRIVER = """
import json, sys
from jump import jump_search
for n, key, *values in json.load(sys.stdin):
    try:
        print(json.dumps(jump_search(values[:n], key)))
    except IndexError:
        print(json.dumps("ARRAY_BOUNDS"))
"""
JS_DRIVER = """
import {readFileSync} from "node:fs";
import {cycleSort} from "./cycle.mjs";
for (const values of JSON.parse(readFileSync(0, "utf8"))) {
  const result = cycleSort(values);
  console.log(JSON.stringify(Array.isArray(result) ? result[0] : result));
}
"""


def upstream(family, version, arguments, folder):
    meta = EXTERNAL[family]
    lang = "py" if meta["archive"] == "jump" else "js"
    source = (ROOT / "upstream" / f"{meta['archive']}-{version}.{lang}.txt").read_text()
    if lang == "py":
        (folder / "jump.py").write_text(source)
        (folder / "driver.py").write_text(PYTHON_DRIVER)
        # Isolated mode excludes user paths. Explicitly insert only this specimen directory.
        command = [sys.executable, "-I", "-B", "-c",
                   "import runpy,sys;sys.path.insert(0,'.');runpy.run_path('driver.py',run_name='__main__')"]
    else:
        # Keep the function and its export. Slide past the archived top-level demo.
        start = source.index("/**\n* Implementation of Cycle Sort")
        (folder / "cycle.mjs").write_text(source[:start] + "export { cycleSort }\n")
        (folder / "driver.mjs").write_text(JS_DRIVER)
        node = which("node")
        if node is None:
            raise RuntimeError("Node is needed for the pinned JavaScript specimen.")
        command = [node, "--permission", "--allow-fs-read=" + str(folder), "driver.mjs"]
    result = subprocess.run(command, cwd=folder, env={}, input=json.dumps(arguments),
                            text=True, capture_output=True, check=True, timeout=8)
    return list(map(json.loads, result.stdout.splitlines()))


def replay():
    cases, _ = audit()
    all_results, oracle = [], MiniCOracle()
    for row in cases:
        family = row["family"]
        if family not in EXTERNAL or row["disposition"] != "fault":
            continue
        rows = row["vectors"] + row["holdout_vectors"]
        arguments = [vector["arguments"] for vector in rows]
        outcomes = {}
        for version, source in (("before", row["source"]), ("after", row["references"][0])):
            with TemporaryDirectory(prefix="intentforge-p12-upstream-") as directory:
                original = upstream(family, version, arguments, Path(directory))
            adapted = []
            for vector in rows:
                run = oracle.verify(source, "f", (Vector.model_validate(vector),), ExecutionLimits())
                issue = run.execution.issue
                adapted.append(issue.code if issue else run.observations[0].actual)
            assert original == adapted, (family, version, original, adapted)
            if version == "after":
                assert original == [row["expected"] for row in rows]
            outcomes[version] = original
        all_results.append({"family": family, "arguments": arguments, **outcomes})
    return {"cases": all_results, "inputs": sum(len(row["arguments"]) for row in all_results)}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    report = replay()
    if args.check:
        assert report == json.loads((REPORTS / "phase12-upstream-v1.json").read_text())
        print(f"Replayed both upstream versions on {report['inputs']} inputs.")
    else:
        print(json.dumps(report, indent=2))
