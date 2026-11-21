"""Audit frozen Phase 8.5 data against the historical corpus and phases."""
import json

from .phase65_audit import HISTORICAL, audit as audit_corpus
from .phase65_fixtures import ROOT as PHASE65_ROOT
from .phase7_fixtures import ROOT as PHASE7_ROOT
from .phase75_fixtures import ROOT as PHASE75_ROOT
from .phase8_fixtures import ROOT as PHASE8_ROOT
from .phase85_fixtures import ROOT, fixtures


def audit():
    return audit_corpus(ROOT, fixtures, (HISTORICAL, PHASE65_ROOT, PHASE7_ROOT, PHASE75_ROOT, PHASE8_ROOT))


if __name__ == "__main__":
    print(json.dumps(audit()[1], indent=2))
