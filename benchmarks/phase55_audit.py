"""Check the exact frozen corpus and record independent-family exclusions."""
from collections import Counter, defaultdict
from difflib import SequenceMatcher
from hashlib import sha256
from itertools import combinations
import json
from pathlib import Path

from ai.correction_safety import repair_key
from benchmarks.phase5_evaluate import historical_sources, shape

DATA = Path(__file__).with_name("data") / "phase55"
CASE_HASH = "$(python -c 'import json;print(json.load(open("benchmarks/data/phase55/manifest-v1.json"))["sha256"])')"


def splice_signature(source, fixed):
    before, after = shape(source), shape(fixed)
    return tuple((tuple(row[0] for row in before[a:b]), tuple(row[0] for row in after[c:d]))
                 for kind, a, b, c, d in SequenceMatcher(None, before, after, autojunk=False).get_opcodes()
                 if kind != "equal")


def audit():
    raw = (DATA / "cases-v1.json").read_bytes()
    manifest = json.loads((DATA / "manifest-v1.json").read_text())
    assert sha256(raw).hexdigest() == CASE_HASH == manifest["sha256"], "The frozen Phase 5.5 corpus changed."
    assert sha256((DATA / "TheAlgorithms-MIT.md").read_bytes()).hexdigest() == manifest["upstream_sha256"]["LICENSE.md"]
    rows = json.loads(raw)
    assert len({row["case_id"] for row in rows}) == len(rows)
    grouped = defaultdict(set)
    specifications = defaultdict(set)
    fixtures = defaultdict(set)
    templates = defaultdict(set)
    for row in rows:
        family, partition = row["source_family"], row["partition"]
        grouped[family].add(partition)
        specifications[row["specification"]].add(family)
        fixtures[json.dumps([row["input_vectors"], row["expected_outputs"]])].add(family)
        for reference in row["reference_repairs"]:
            templates[splice_signature(row["mini_c_source"], reference)].add(partition)
        if row["origin_group"] == "external_adaptation":
            upstream = row["source_origin"].split(f"/blob/{manifest['revision']}/")[1]
            assert row["source_license"] == "MIT" and upstream in manifest["upstream_sha256"]
            assert upstream not in manifest["quarantined_upstream"]
    assert all(len(parts) == 1 for parts in grouped.values())
    partitions = dict(sorted(Counter(row["partition"] for row in rows).items()))
    assert partitions == manifest["partitions"]
    history = set()
    for path in sorted(DATA.parent.glob("*.json")):
        document = json.loads(path.read_text())
        history.update(historical_sources(document))
        # Historical reference arrays were not included by the Phase 5 walker.
        if isinstance(document, dict) and isinstance(document.get("families"), list):
            for case in document["families"]:
                if isinstance(case, dict):
                    history.update(case.get("references", ()))
    old_exact = {repair_key(source) for source in history}
    old_alpha = {shape(source) for source in history}
    alpha = {row["case_id"]: shape(row["mini_c_source"]) for row in rows}
    exact = [row["case_id"] for row in rows if repair_key(row["mini_c_source"]) in old_exact]
    renamed = [key for key, tokens in alpha.items() if tokens in old_alpha]
    quarantine = {row["source_family"] for row in rows if row["case_id"] in set(exact) | set(renamed)}
    near = []
    structural = []
    for left, right in combinations(rows, 2):
        if left["source_family"] == right["source_family"]:
            continue
        a, b = alpha[left["case_id"]], alpha[right["case_id"]]
        if min(len(a), len(b)) < .75 * max(len(a), len(b)):
            continue
        if a == b:
            structural.append([left["case_id"], right["case_id"]])
            quarantine.update((left["source_family"], right["source_family"]))
        if left["partition"] != right["partition"]:
            likeness = SequenceMatcher(None, a, b, autojunk=False).ratio()
            if likeness >= .90:
                near.append({"cases": [left["case_id"], right["case_id"]], "ratio": round(likeness, 3)})
                quarantine.add(left["source_family"] if right["partition"] == "final" else right["source_family"])
    report = {"data_sha256": CASE_HASH, "partitions": partitions, "families": len(grouped),
              "historical_sources_checked": len(history), "historical_exact": exact, "historical_alpha": renamed,
              "interfamily_exact_structure": structural, "near_cross_partition": near,
              "reused_specifications": [sorted(group) for group in specifications.values() if len(group) > 1],
              "reused_full_fixtures": [sorted(group) for group in fixtures.values() if len(group) > 1],
              "repair_templates_shared_across_partitions": sum(len(parts) > 1 for parts in templates.values()),
              "quarantined_upstream": manifest["quarantined_upstream"], "quarantined_families": sorted(quarantine)}
    return [row for row in rows if row["source_family"] not in quarantine], report


if __name__ == "__main__":
    cases, report = audit()
    print(json.dumps(report, indent=2))
