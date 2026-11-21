"""Verify the frozen Phase 6 corpus and exclude historical near matches."""
from collections import Counter, defaultdict
from difflib import SequenceMatcher
from hashlib import sha256
from itertools import combinations
import json
from pathlib import Path

from ai.correction_safety import repair_key
from .phase5_evaluate import historical_sources, shape
from .phase55_audit import splice_signature

ROOT = Path(__file__).with_name("data") / "phase6"
CASE_HASH = 'e438de6cc64af3656d4a0b8ab0e95af2d6617c4d7e5e07a2cff9b2ecfb41d22c'


def extended_sources(document):
    yield from historical_sources(document)
    pending = [document]
    while pending:
        item = pending.pop()
        if isinstance(item, dict):
            for key in ("references", "reference_repairs", "acceptable_alternatives", "mini_c_source"):
                value = item.get(key, ())
                if isinstance(value, str):
                    value = (value,)
                if isinstance(value, (list, tuple)):
                    yield from (text for text in value if isinstance(text, str) and "{" in text)
            pending.extend(item.values())
        elif isinstance(item, list):
            pending.extend(item)


def ratio(left, right, threshold):
    if min(len(left), len(right)) < threshold / (2-threshold) * max(len(left), len(right)):
        return 0.0
    return SequenceMatcher(None, left, right, autojunk=False).ratio()


def audit():
    payload = (ROOT / "cases-v1.json").read_bytes()
    manifest = json.loads((ROOT / "manifest-v1.json").read_text())
    assert sha256(payload).hexdigest() == CASE_HASH == manifest["case_sha256"]
    assert sha256((ROOT / "TheAlgorithms-MIT.md").read_bytes()).hexdigest() == manifest["upstream_sha256"]["LICENSE.md"]
    cases = json.loads(payload)
    assert len({row["id"] for row in cases}) == len(cases)
    partitions = defaultdict(set)
    for row in cases:
        partitions[row["family"]].add(row["partition"])
        origin = row["provenance"]
        if origin["group"] == "external_adaptation":
            path = origin["origin"].split(f"/blob/{manifest['revision']}/")[1]
            assert path in manifest["upstream_sha256"] and origin["license"] == "MIT"
    assert all(len(splits) == 1 for splits in partitions.values())
    assert dict(Counter(row["partition"] for row in cases)) == manifest["partitions"]
    history = {source for path in ROOT.parent.rglob("*.json") if ROOT not in path.parents
               for source in extended_sources(json.loads(path.read_text()))}
    indexed = [(sha256(source.encode()).hexdigest(), shape(source)) for source in sorted(history)]
    historical_keys = {repair_key(source) for source in history}
    historical_shapes = {row[1] for row in indexed}
    quarantined = set()
    overlaps = []
    alpha = {row["id"]: shape(row["source"]) for row in cases}
    for row in cases:
        current = alpha[row["id"]]
        if repair_key(row["source"]) in historical_keys or current in historical_shapes:
            quarantined.add(row["family"])
            overlaps.append({"case": row["id"], "match": "exact" if repair_key(row["source"]) in historical_keys else "alpha"})
        elif len(current) >= 25:
            for digest, other in indexed:
                likeness = ratio(current, other, .94)
                if likeness >= .94:
                    quarantined.add(row["family"])
                    overlaps.append({"case": row["id"], "match": "near", "ratio": round(likeness, 4), "historical_sha256": digest})
                    break
    cross = []
    repeated_specs, repeated_vectors = [], []
    for left, right in combinations(cases, 2):
        if left["family"] == right["family"]:
            continue
        ids = [left["id"], right["id"]]
        a, b = (alpha[key] for key in ids)
        if left["specification"] == right["specification"]:
            repeated_specs.append(ids)
        if left["vectors"] == right["vectors"]:
            repeated_vectors.append(ids)
        if a == b:
            quarantined.update((left["family"], right["family"]))
            cross.append({"cases": ids, "match": "alpha"})
        elif left["partition"] != right["partition"] and len(a) >= 25 and len(b) >= 25:
            similarity = ratio(a, b, .90)
            if similarity >= .90:
                cross.append({"cases": ids, "match": "near", "ratio": round(similarity, 4)})
                if not {left["family"], right["family"]} & quarantined:
                    quarantined.add(left["family"] if right["partition"] == "final" else right["family"])
    admitted = [case for case in cases if case["family"] not in quarantined]
    templates = defaultdict(set)
    for row in admitted:
        for reference in row["references"]:
            templates[splice_signature(row["source"], reference)].add(row["partition"])
    return admitted, {
        "sha256": CASE_HASH, "historical_sources": len(history),
        "frozen_partitions": manifest["partitions"], "admitted_partitions": dict(sorted(Counter(row["partition"] for row in admitted).items())),
        "quarantined_families": sorted(quarantined), "historical_overlaps": overlaps, "interfamily_overlaps": cross,
        "same_full_specification": repeated_specs, "same_full_vectors": repeated_vectors,
        "shared_cross_partition_edit_shapes": sum(len(splits) > 1 for splits in templates.values()),
    }


if __name__ == "__main__":
    _, report = audit()
    print(json.dumps(report, indent=2))
