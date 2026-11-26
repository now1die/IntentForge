"""Score fixed discovery and held-out inputs across identical public profiles."""
import argparse
import json
from .phase12_evaluate import projection_row, metrics, metamorphic, live, latency, stable, REPORTS, MiniCOracle
from .phase115_evaluate import archived_cases
from .phase12_fixtures import fixtures as previous
from .phase13_audit import audit

VERSIONS = (105, 11, 115, 12, 13)


def evaluate(cases):
    oracle = MiniCOracle()
    profiles = {}
    for version in VERSIONS:
        settings = {f"phase{version}":True}
        rows, times = zip(*(projection_row(oracle, row, settings) for row in cases))
        profiles[str(version)] = dict(rows=rows,metrics=metrics(rows),latency=latency(times))
    archive = [row for row,_ in archived_cases()]
    archive.extend(row for row in previous() if row["fault_origin"]=="adapted-real-defect")
    return {"profiles":profiles, "archive":[projection_row(oracle,row,{"phase13":True})[0] for row in archive],
            "metamorphic":metamorphic(oracle,cases,"phase13")}


if __name__=="__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--live",action="store_true")
    parser.add_argument("--check",action="store_true")
    args = parser.parse_args()
    cases = [row for row in audit()[0] if row["partition"]=="final"]
    report = json.loads(json.dumps(live(cases,VERSIONS) if args.live else evaluate(cases)))
    if args.check:
        kind = "live" if args.live else "static"
        assert stable(report) == stable(json.loads((REPORTS/f"phase13-{kind}-v1.json").read_text()))
        print(f"Verified {len(cases)} Phase 13 cases.")
    else:
        print(json.dumps(report,indent=2))
