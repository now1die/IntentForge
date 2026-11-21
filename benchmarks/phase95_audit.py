"""Verify Phase 9.5 fixture integrity and quarantine older source or metadata overlaps."""
import json
from collections import defaultdict

from .phase65_audit import HISTORICAL, audit as audit_corpus
from .phase65_fixtures import ROOT as PHASE65
from .phase7_fixtures import ROOT as PHASE7
from .phase75_fixtures import ROOT as PHASE75
from .phase8_fixtures import ROOT as PHASE8
from .phase85_fixtures import ROOT as PHASE85
from .phase9_fixtures import ROOT as PHASE9
from .phase95_fixtures import ROOT, JAVA, EXTERNAL, fixtures


def audit():
    admitted, results = audit_corpus(ROOT,fixtures,(HISTORICAL,PHASE65,PHASE7,PHASE75,PHASE8,PHASE85,PHASE9))
    manifest = json.loads((ROOT/"manifest-v1.json").read_text())
    assert manifest["external_sources"] == {key:list(value) for key,value in EXTERNAL.items()}
    previous_commits = {c["provenance"].get("after") for c in json.loads((PHASE9/"cases-v1.json").read_text())}
    partitions = defaultdict(set)
    for case in fixtures():
        if case["family"] in EXTERNAL:
            partitions[case["provenance"]["repository"]].add(case["partition"])
    assert all(len(splits)==1 for splits in partitions.values())
    for _,(repo,_,archive,before,after,_) in EXTERNAL.items():
        assert before != after and before not in previous_commits and after not in previous_commits
        suffix = "java" if repo==JAVA else "js"
        license_name = "LICENSE-Java.txt" if repo==JAVA else "LICENSE-JavaScript.txt"
        for filename in (f"{archive}-before.{suffix}",f"{archive}-after.{suffix}",license_name):
            assert filename in manifest["upstream_sha256"]
    results["upstream_partitions"] = {repo:sorted(splits) for repo,splits in partitions.items()}
    results["admitted_external_families"] = sorted({case["family"] for case in admitted if case["family"] in EXTERNAL})
    return admitted,results


if __name__=="__main__":
    print(json.dumps(audit()[1],indent=2))
