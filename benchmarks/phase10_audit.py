"""Check the new freeze against every historical benchmark corpus."""
from collections import defaultdict
import json

from .phase65_audit import HISTORICAL, audit as audit_corpus, records
from .phase65_fixtures import ROOT as PHASE65
from .phase7_fixtures import ROOT as PHASE7
from .phase75_fixtures import ROOT as PHASE75
from .phase8_fixtures import ROOT as PHASE8
from .phase85_fixtures import ROOT as PHASE85
from .phase9_fixtures import ROOT as PHASE9
from .phase95_fixtures import ROOT as PHASE95
from .phase10_fixtures import EXTERNAL, JAVA, ROOT, fixtures

HISTORY = (HISTORICAL, PHASE65, PHASE7, PHASE75, PHASE8, PHASE85, PHASE9, PHASE95)


def audit():
    rows, report = audit_corpus(ROOT, fixtures, HISTORY)
    manifest = json.loads((ROOT/"manifest-v1.json").read_text())
    assert manifest["external_sources"] == {key:list(value) for key,value in EXTERNAL.items()}
    prior_commits = {row[key] for directory in HISTORY for path in directory.rglob("*.json")
                     for row in records(json.loads(path.read_text())) for key in ("before","after")
                     if isinstance(row.get(key),str) and len(row[key])==40}
    splits = defaultdict(set)
    for row in fixtures():
        if row["family"] in EXTERNAL:
            splits[row["provenance"]["repository"]].add(row["partition"])
    assert all(len(partitions)==1 for partitions in splits.values())
    for repo,_,archive,before,after,_ in EXTERNAL.values():
        suffix = "java" if repo==JAVA else "py"
        license_file = "LICENSE-Java.txt" if repo==JAVA else f"LICENSE-Python-{archive}.txt"
        assert before != after and not {before,after} & prior_commits
        assert {f"{archive}-before.{suffix}",f"{archive}-after.{suffix}",license_file} <= manifest["upstream_sha256"].keys()
    report["upstream_partitions"] = {repo:sorted(values) for repo,values in splits.items()}
    report["admitted_external_families"] = sorted({row["family"] for row in rows if row["family"] in EXTERNAL})
    return rows, report


if __name__=="__main__":
    print(json.dumps(audit()[1],indent=2))
