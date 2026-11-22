"""Verify the freeze, original source hashes and family separation."""
from collections import defaultdict
import json

from .phase65_audit import audit as audit_corpus, records
from .phase10_audit import HISTORY
from .phase10_fixtures import ROOT as PHASE10
from .phase105_fixtures import ROOT as PHASE105
from .phase11_fixtures import ROOT as PHASE11
from .phase115_fixtures import EXTERNAL, ROOT, fixtures


def audit():
    history=(*HISTORY,PHASE10,PHASE105,PHASE11)
    admitted,report=audit_corpus(ROOT,fixtures,history)
    manifest=json.loads((ROOT/"manifest-v1.json").read_text())
    assert manifest["external_sources"]=={key:list(value) for key,value in EXTERNAL.items()}
    prior={row[key] for directory in history for path in directory.rglob("*.json")
           for row in records(json.loads(path.read_text())) for key in ("before","after")
           if isinstance(row.get(key),str) and len(row[key])==40}
    groups=defaultdict(set)
    for row in fixtures():
        if row["family"] in EXTERNAL:
            groups[row["provenance"]["repository"]].add(row["partition"])
    assert all(len(splits)==1 for splits in groups.values())
    for repository,_,archive,before,after,_,_ in EXTERNAL.values():
        name=repository.rsplit("/",1)[1]
        suffix={"Python":"py","JavaScript":"js","Java":"java"}[name]
        assert before!=after and not {before,after}&prior
        assert {f"{archive}-before.{suffix}",f"{archive}-after.{suffix}",f"LICENSE-{name}.txt"}<=manifest["upstream_sha256"].keys()
    report["upstream_partitions"]={name:sorted(splits) for name,splits in groups.items()}
    report["admitted_external_families"]=sorted({row["family"] for row in admitted if row["family"] in EXTERNAL})
    return admitted,report


if __name__=="__main__":
    print(json.dumps(audit()[1],indent=2))
