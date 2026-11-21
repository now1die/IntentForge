"""Audit Phase 7 sources and references against all Phase 1–6.5 corpora."""
import json

from .phase65_audit import HISTORICAL, audit as audit_corpus
from .phase65_fixtures import ROOT as PHASE65_ROOT
from .phase7_fixtures import ROOT, fixtures


def audit():
    return audit_corpus(ROOT, fixtures, (HISTORICAL, PHASE65_ROOT))


if __name__ == "__main__":
    print(json.dumps(audit()[1], indent=2))
