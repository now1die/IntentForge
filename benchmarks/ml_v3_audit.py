"""Check program families, sources, normalized tokens and ASTs across splits."""
import json

from .ml_v3_data import DEVELOPMENT, FINAL, build, read
from .phase25_audit import Source, _legacy, check
from .phase25_data import DEVELOPMENT as V2_DEVELOPMENT, FINAL as V2_FINAL


def audit():
    historical = list(_legacy())
    for path in (V2_DEVELOPMENT, V2_FINAL):
        for case in read(path):
            historical.extend(Source(text, case["id"], "historical")
                              for text in [case["source"], *case["accepted"], *case.get("rejected", [])])
    result = check(read(DEVELOPMENT), read(FINAL) if FINAL.is_file() else [], historical=historical)
    if json.loads(DEVELOPMENT.read_text()) != build():
        result["issues"].append("Development data does not match the authored examples")
    return result


if __name__ == "__main__":
    result = audit()
    print(json.dumps(result, indent=2))
    raise SystemExit(bool(result["issues"] or result["cross_split_near_pairs"]))
