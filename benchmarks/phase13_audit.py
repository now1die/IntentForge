"""Validate partitioning, source overlap and the frozen revision pairs."""
from collections import Counter
from hashlib import sha256
import json

from .phase12_audit import HISTORY, PHASE10, PHASE105, PHASE11, PHASE115
from .phase12_fixtures import ROOT as PHASE12
from .phase65_audit import audit as audit_corpus, records
from .phase13_fixtures import PINS, ROOT, fixtures


def audit():
    history = (*HISTORY, PHASE10, PHASE105, PHASE11, PHASE115, PHASE12)
    admitted, report = audit_corpus(ROOT, fixtures, history)
    manifest = json.loads((ROOT/"manifest-v1.json").read_text())
    assert manifest["revisions_sha256"] == sha256((ROOT/"revisions.json").read_bytes()).hexdigest()
    prior = {row[key] for directory in history for path in directory.rglob("*.json")
             for row in records(json.loads(path.read_text())) for key in ("before","after") if isinstance(row.get(key),str)}
    reused = {family for family, source in PINS.items() if {source["before"],source["after"]} & prior}
    admitted = [row for row in admitted if row["family"] not in reused]
    report["historical_revision_overlap"] = sorted(reused)
    report["quarantined_families"] = sorted(set(report["quarantined_families"]) | reused)
    report["admitted_partitions"] = dict(Counter(row["partition"] for row in admitted))
    for row in admitted:
        assert {tuple(v["arguments"]) for v in row["vectors"]}.isdisjoint(tuple(v["arguments"]) for v in row["holdout_vectors"])
    return admitted, report


if __name__=="__main__":
    print(json.dumps(audit()[1],indent=2))
