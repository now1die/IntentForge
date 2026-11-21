"""Check the Phase 9 freeze, real-defect records and overlap with earlier cohorts."""
import json

from .phase65_audit import HISTORICAL, audit as audit_corpus
from .phase65_fixtures import ROOT as PHASE65_ROOT
from .phase7_fixtures import ROOT as PHASE7_ROOT
from .phase75_fixtures import ROOT as PHASE75_ROOT
from .phase8_fixtures import ROOT as PHASE8_ROOT
from .phase85_fixtures import ROOT as PHASE85_ROOT
from .phase9_fixtures import EXTERNAL, ROOT, fixtures


def audit():
    cases, finding = audit_corpus(ROOT, fixtures, (HISTORICAL, PHASE65_ROOT, PHASE7_ROOT, PHASE75_ROOT,
                                                  PHASE8_ROOT, PHASE85_ROOT))
    manifest = json.loads((ROOT/"manifest-v1.json").read_text())
    assert manifest["external"] == EXTERNAL
    for family, item in EXTERNAL.items():
        assert len(item["before"]) == len(item["after"]) == 40 and item["before"] != item["after"]
        for archive in (f"{item['archive']}-before.py", f"{item['archive']}-after.py", item["license_file"]):
            assert archive in manifest["upstream_sha256"]
        assert (ROOT/"upstream"/item["license_file"]).read_text().startswith("MIT License")
    finding["external_families"] = {key: {"admitted":any(row["family"]==key for row in cases), **value}
                                    for key,value in EXTERNAL.items()}
    return cases,finding


if __name__ == "__main__":
    print(json.dumps(audit()[1],indent=2))
