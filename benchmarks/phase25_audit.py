"""Phase 2.5 split checks against preserved training and published corpora."""

from collections import Counter
from dataclasses import dataclass
import json

from compiler.parser import parse
from compiler.semantic_analyzer import analyze_source_semantics

from .corpus import DATA, load_cases, near_duplicate_pairs, template_key, training_sources
from .phase25_data import DEVELOPMENT, FINAL, generate


@dataclass(frozen=True)
class Source:
    text: str
    id: str
    split: str


def _ast_key(source):
    parsed = parse(source)
    if not parsed.valid:
        return None

    def normalize(item):
        if isinstance(item, dict):
            return tuple((k, normalize(v)) for k, v in item.items() if k not in {"span", "name", "value"}
                         or (k == "value" and isinstance(v, dict)))
        if isinstance(item, list):
            return tuple(normalize(value) for value in item)
        return item

    return normalize(parsed.ast.to_dict())


def _legacy():
    for case in load_cases(corpus="all"):
        yield Source(case["source"], case["id"], "historical")
        for source in case["acceptable_sources"] + case["rejected_sources"]:
            yield Source(source, case["id"], "historical")
    for name in ["phase2-development-v1.json", "phase2-evaluation-v1.json"]:
        for case in json.loads((DATA / name).read_text())["cases"]:
            yield Source(case["source"], case["id"], "historical")
            references = case["accepted"] if isinstance(case["accepted"], list) else [case["accepted"]]
            for text in references:
                yield Source(text, case["id"], "historical")
    for index, (source, fixed, _) in enumerate(training_sources()):
        yield Source(source, f"archive-{index}", "historical")
        yield Source(fixed, f"archive-{index}", "historical")


def check(development, final, *, historical=None, check_near=True):
    issues = []
    rows = [*development, *final]
    if len({case["id"] for case in rows}) != len(rows):
        issues.append("Duplicate case IDs")
    for case in rows:
        if case["split"] != "final" and case in final:
            issues.append(f"Invalid final split on {case['id']}")
    families = {}
    for case in rows:
        if families.setdefault(case["family"], case["split"]) != case["split"]:
            issues.append(f"Program family crosses splits: {case['family']}")
        if case.get("ambiguous") and case["accepted"]:
            issues.append(f"Ambiguous label includes a single accepted repair: {case['id']}")
        for reference in case["accepted"]:
            if not analyze_source_semantics(reference).success:
                issues.append(f"Compiler-invalid reference: {case['id']}")
    legacy = list(_legacy() if historical is None else historical)
    signatures = [{}, {}, {}]
    ast_cache = {}
    normalized_inputs = {}
    for case in rows:
        key = template_key(case["source"])
        previous = normalized_inputs.setdefault(key, case)
        if previous is not case and previous["family"] != case["family"]:
            issues.append(f"{case['id']} repeats another input family")
    active = [
        Source(text, case["id"], case["split"])
        for case in rows for text in [case["source"], *case["accepted"], *case.get("rejected", [])]
    ]
    for row in [*legacy, *active]:
        template = template_key(row.text)
        if template not in ast_cache:
            ast_cache[template] = _ast_key(row.text)
        for table, key, name in zip(signatures, [row.text, template, ast_cache[template]], ["source", "tokens", "AST"], strict=True):
            if key is None:
                continue
            previous = table.setdefault(key, row)
            if previous.split != row.split:
                issues.append(f"{row.id} overlaps {previous.split} {name} ({previous.id})")
    near = []
    if check_near:
        representative = {}
        for row in [*legacy, *active]:
            representative.setdefault((row.split, template_key(row.text)), row)
        search_rows = [{"id": str(index), "source": row.text}
                       for index, row in enumerate(representative.values())]
        sources = list(representative.values())
        for left, right, similarity in near_duplicate_pairs(search_rows, paths=(), threshold=.94):
            a, b = sources[int(left)], sources[int(right)]
            if a.split != b.split:
                near.append((a.id, b.id, similarity))
    return {"cases": Counter(case["split"] for case in rows), "families": Counter(families.values()),
            "near_input_and_reference_pairs_threshold": .94, "cross_split_near_pairs": sorted(set(near)),
            "issues": sorted(set(issues))}


if __name__ == "__main__":
    raw = json.loads(DEVELOPMENT.read_text())
    result = check(raw["cases"], json.loads(FINAL.read_text())["cases"] if FINAL.is_file() else [])
    if raw != generate():
        result["issues"].append("Development data differs from the committed generator")
    print(json.dumps(result, indent=2))
    raise SystemExit(bool(result["issues"] or result["cross_split_near_pairs"]))
