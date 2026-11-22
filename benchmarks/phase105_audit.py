"""Check pinned Phase 10.5 provenance and overlap against prior corpora."""
from collections import defaultdict
import json

from .phase65_audit import audit as audit_corpus, records
from .phase10_audit import HISTORY
from .phase10_fixtures import ROOT as PHASE10
from .phase105_fixtures import EXTERNAL, ROOT, fixtures


def audit():
    history = (*HISTORY,PHASE10)
    admitted, report = audit_corpus(ROOT,fixtures,history)
    manifest = json.loads((ROOT/"manifest-v1.json").read_text())
    assert manifest["external_sources"]=={key:list(value) for key,value in EXTERNAL.items()}
    prior = {row[key] for directory in history for path in directory.rglob("*.json")
             for row in records(json.loads(path.read_text())) for key in ("before","after")
             if isinstance(row.get(key),str) and len(row[key])==40}
    groups = defaultdict(set)
    for row in fixtures():
        if row["family"] in EXTERNAL:
            groups[row["provenance"]["repository"]].add(row["partition"])
    assert all(len(group)==1 for group in groups.values())
    for repository,_,archive,before,after,_,_ in EXTERNAL.values():
        upstream = repository.rsplit("/",1)[1]
        suffix = {"Python":"py","JavaScript":"js","Java":"java"}[upstream]
        assert before!=after and not {before,after}&prior
        assert {f"{archive}-before.{suffix}",f"{archive}-after.{suffix}",f"LICENSE-{upstream}.txt"}<=manifest["upstream_sha256"].keys()
    report["upstream_partitions"] = {key:sorted(splits) for key,splits in groups.items()}
    report["admitted_external_families"] = sorted({row["family"] for row in admitted if row["family"] in EXTERNAL})
    return admitted,report


if __name__=="__main__":
    print(json.dumps(audit()[1],indent=2))
