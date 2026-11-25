"""Audit the frozen Phase 12 cohort against the entire historical corpus."""
import json

from .phase10_audit import HISTORY
from .phase10_fixtures import ROOT as PHASE10
from .phase105_fixtures import ROOT as PHASE105
from .phase11_fixtures import ROOT as PHASE11
from .phase115_fixtures import ROOT as PHASE115
from .phase65_audit import audit as audit_corpus, records
from .phase12_fixtures import EXTERNAL, ROOT, fixtures


def audit():
    history = (*HISTORY, PHASE10, PHASE105, PHASE11, PHASE115)
    admitted, report = audit_corpus(ROOT, fixtures, history)
    manifest = json.loads((ROOT / "manifest-v1.json").read_text())
    assert manifest["external_sources"] == EXTERNAL
    old_pins = {row[key] for folder in history for path in folder.rglob("*.json")
                for row in records(json.loads(path.read_text())) for key in ("before", "after")
                if isinstance(row.get(key), str)}
    for source in EXTERNAL.values():
        assert {source["before"], source["after"]}.isdisjoint(old_pins)
        assert source["before"] != source["after"]
    for row in admitted:
        assert {tuple(v["arguments"]) for v in row["vectors"]}.isdisjoint(
            tuple(v["arguments"]) for v in row["holdout_vectors"])
    report["upstream_repositories"] = sorted({row["repository"] for row in EXTERNAL.values()})
    return admitted, report


if __name__ == "__main__":
    print(json.dumps(audit()[1], indent=2))
