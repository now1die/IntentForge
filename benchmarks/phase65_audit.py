"""Check the independent corpus freeze, upstream hashes and historical overlap."""
from collections import Counter, defaultdict
from hashlib import sha256
from itertools import combinations
import json
from pathlib import Path

from .phase5_evaluate import shape
from .phase6_audit import extended_sources, ratio
from .phase55_audit import splice_signature
from .phase65_fixtures import ROOT, fixtures
from ai.correction_safety import repair_key

HISTORICAL = Path(__file__).with_name("data")


def records(document):
    if isinstance(document, dict):
        yield document
        for value in document.values():
            yield from records(value)
    elif isinstance(document, list):
        for value in document:
            yield from records(value)


def texts(row):
    return (row["source"], *row["references"])


def encoded(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":"))


def audit(root=ROOT, fixture_factory=fixtures, history_roots=(HISTORICAL,)):
    payload = (root/"cases-v1.json").read_bytes()
    manifest = json.loads((root/"manifest-v1.json").read_text())
    cases = json.loads(payload)
    assert sha256(payload).hexdigest() == manifest["case_sha256"]
    assert cases == fixture_factory()
    assert len({row["id"] for row in cases}) == len(cases)
    assert dict(Counter(row["partition"] for row in cases)) == manifest["partitions"]
    for path, expected in manifest["upstream_sha256"].items():
        assert sha256((root/"upstream"/Path(path).name).read_bytes()).hexdigest() == expected
    history, specs, vectors = set(), set(), set()
    for path in sorted(path for directory in history_roots for path in directory.rglob("*.json")):
        document = json.loads(path.read_text())
        history.update(extended_sources(document))
        for row in records(document):
            for key in ("specification", "requirement"):
                if row.get(key):
                    specs.add(encoded(row[key]))
            for key in ("vectors", "examples", "tests", "holdout_vectors"):
                if isinstance(row.get(key), list) and row[key]:
                    values = row[key]
                    if all(isinstance(item, dict) and ("args" in item or "arguments" in item)
                           and ("expected" in item or "expected_return" in item) for item in values):
                        vectors.add(encoded([{"arguments": item.get("arguments", item.get("args")),
                                              "expected": item.get("expected", item.get("expected_return"))} for item in values]))
    prior_keys = {repair_key(source) for source in history}
    prior_shapes = {shape(source): sha256(source.encode()).hexdigest() for source in sorted(history)}
    families, shapes = defaultdict(set), {}
    quarantined, historical, across, full_metadata = set(), [], [], []
    for row in cases:
        family = row["family"]
        families[family].add(row["partition"])
        provenance = row["provenance"]
        if provenance["group"] == "external_adaptation":
            path = provenance["origin"].split(f"/blob/{manifest['revision']}/", 1)[1]
            assert provenance["license"] == "MIT" and path in manifest["upstream_sha256"]
        shapes[row["id"]] = tuple(shape(source) for source in texts(row))
        for candidate, normalized in zip(texts(row), shapes[row["id"]], strict=True):
            if repair_key(candidate) in prior_keys or normalized in prior_shapes:
                matched = {"match": "exact" if repair_key(candidate) in prior_keys else "alpha"}
            else:
                match = max(((ratio(normalized, old, .94), digest) for old, digest in prior_shapes.items()),
                            default=(0, "")) if len(normalized) >= 25 else (0, "")
                matched = {"match": "near", "ratio": round(match[0], 4), "historical_sha256": match[1]} if match[0] >= .94 else None
            if matched:
                quarantined.add(family)
                historical.append({"case": row["id"], **matched})
        hits = [key for key, index in [("specification", specs), ("vectors", vectors), ("holdout_vectors", vectors)]
                if row.get(key) and encoded(row[key]) in index]
        if hits:
            quarantined.add(family)
            full_metadata.append({"case": row["id"], "fields": hits})
    assert all(len(splits) == 1 for splits in families.values())
    for left, right in combinations(cases, 2):
        if left["partition"] == right["partition"]:
            continue
        overlap = max((1 if a == b else ratio(a,b,.90) if min(len(a),len(b)) >= 25 else 0
                       for a in shapes[left["id"]] for b in shapes[right["id"]]), default=0)
        repeated = [key for key in ("specification", "vectors", "holdout_vectors") if left.get(key) and left[key] == right.get(key)]
        if (left.get("holdout_vectors") and left["holdout_vectors"] == right.get("vectors")
                or right.get("holdout_vectors") and right["holdout_vectors"] == left.get("vectors")):
            repeated.append("cross_mode_vectors")
        if overlap >= .90 or repeated:
            across.append({"left": left["id"], "right": right["id"], "similarity": round(overlap, 4), "repeated": repeated})
            if not {left["family"], right["family"]} & quarantined:
                quarantined.add((left if right["partition"] == "final" else right)["family"])
    admitted = [row for row in cases if row["family"] not in quarantined]
    templates = defaultdict(set)
    for row in admitted:
        for reference in row["references"]:
            templates[splice_signature(row["source"], reference)].add(row["partition"])
    return admitted, {
        "sha256": manifest["case_sha256"], "historical_sources": len(history),
        "frozen_partitions": manifest["partitions"], "admitted_partitions": dict(Counter(row["partition"] for row in admitted)),
        "quarantined_families": sorted(quarantined), "historical_overlaps": historical,
        "repeated_historical_metadata": full_metadata, "cross_partition_overlaps": across,
        "shared_cross_partition_edit_shapes": sum(len(splits)>1 for splits in templates.values()),
    }


if __name__ == "__main__":
    print(json.dumps(audit()[1], indent=2))
